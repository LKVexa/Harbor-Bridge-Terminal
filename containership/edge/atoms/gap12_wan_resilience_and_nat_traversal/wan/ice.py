"""ICE-compatible candidate model and connectivity-check state machine
(G12-A003) — RFC 8445 / RFC 7675.

Implemented: host / srflx / prflx / relay candidates with RFC 8445 5.1.2
priorities and 5.1.1.3 foundations; pair priority (6.1.2.3); checklist
construction with redundancy pruning (6.1.2.4) and a hard pair ceiling
(``MAX_PAIRS``, default 100 as RFC 8445 recommends) so hostile candidate sets
cannot cause a combinatorial explosion; pair states Frozen / Waiting /
In-Progress / Succeeded / Failed with only legal transitions; triggered-check
queue; peer-reflexive candidate learning; controlling/controlled role conflict
resolution by tie-breaker (7.3.1.1); regular nomination; consent freshness
(RFC 7675: consent lost after 30 s without a response).

The check *transport* is supplied by the caller (``check(pair) -> bool``) so the
same machine drives the lab UDP hole-punch adapter.

Unsupported (explicit): aggressive nomination (deprecated), ICE-TCP (RFC 6544),
and trickle ICE (RFC 8838) — candidates are delivered as a complete set.
"""
from __future__ import annotations

import functools
import hashlib
import ipaddress
from dataclasses import dataclass, field

TYPE_PREF = {"host": 126, "prflx": 110, "srflx": 100, "relay": 0}
MAX_CANDIDATES = 32
MAX_PAIRS = 100
CONSENT_TIMEOUT = 30.0
STATES = ("frozen", "waiting", "in-progress", "succeeded", "failed")
LEGAL = {
    "frozen": {"waiting", "failed"},
    "waiting": {"in-progress", "failed"},
    "in-progress": {"succeeded", "failed", "waiting"},  # waiting = re-queued by a triggered check
    "succeeded": set(),
    "failed": {"waiting"},                               # a triggered check may revive a failed pair
}


class IllegalTransition(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    type: str
    ip: str
    port: int
    component: int = 1
    base: tuple[str, int] | None = None
    server: str | None = None
    local_pref: int = 65535

    def __post_init__(self):
        if self.type not in TYPE_PREF:
            raise ValueError(f"unknown candidate type {self.type!r}")
        ipaddress.ip_address(self.ip)
        if not 0 < self.port < 65536 or not 1 <= self.component <= 256:
            raise ValueError("port/component out of range")

    @functools.cached_property
    def priority(self) -> int:
        return (TYPE_PREF[self.type] << 24) + (self.local_pref << 8) + (256 - self.component)

    @functools.cached_property
    def foundation(self) -> str:
        base_ip = (self.base or (self.ip, self.port))[0]
        key = f"{self.type}|{base_ip}|{self.server or ''}|udp"
        return hashlib.sha256(key.encode()).hexdigest()[:8]

    @functools.cached_property
    def family(self) -> int:
        return ipaddress.ip_address(self.ip).version


@dataclass
class Pair:
    local: Candidate
    remote: Candidate
    controlling: bool
    state: str = "frozen"
    nominated: bool = False
    last_response: float | None = None

    @property
    def priority(self) -> int:
        g, d = (self.local.priority, self.remote.priority) if self.controlling else (self.remote.priority, self.local.priority)
        return (1 << 32) * min(g, d) + 2 * max(g, d) + (1 if g > d else 0)

    @property
    def foundation(self) -> tuple[str, str]:
        return self.local.foundation, self.remote.foundation

    def move(self, new: str) -> None:
        if new not in LEGAL[self.state]:
            raise IllegalTransition(f"{self.state} -> {new}")
        self.state = new


@dataclass
class Agent:
    controlling: bool
    tie_breaker: int
    local: list[Candidate] = field(default_factory=list)
    remote: list[Candidate] = field(default_factory=list)
    pairs: list[Pair] = field(default_factory=list)
    triggered: list[Pair] = field(default_factory=list)
    selected: Pair | None = None
    pruned: int = 0

    def set_candidates(self, local: list[Candidate], remote: list[Candidate]) -> None:
        if len(local) > MAX_CANDIDATES or len(remote) > MAX_CANDIDATES:
            # keep the highest-priority candidates; never iterate an attacker-sized set
            self.pruned += max(0, len(local) - MAX_CANDIDATES) + max(0, len(remote) - MAX_CANDIDATES)
        self.local = sorted(local, key=lambda c: -c.priority)[:MAX_CANDIDATES]
        self.remote = sorted(_dedupe(remote), key=lambda c: -c.priority)[:MAX_CANDIDATES]
        self._form_checklist()

    def _form_checklist(self) -> None:
        pairs = []
        for lc in self.local:
            for rc in self.remote:
                if lc.component == rc.component and lc.family == rc.family:
                    # RFC 8445 6.1.2.4: srflx locals are replaced by their base
                    l_eff = lc if lc.type != "srflx" else Candidate("host", *(lc.base or (lc.ip, lc.port)),
                                                                    component=lc.component)
                    pairs.append(Pair(l_eff, rc, self.controlling))
        pairs.sort(key=lambda p: -p.priority)
        seen, pruned = set(), []
        for p in pairs:
            key = ((p.local.ip, p.local.port), (p.remote.ip, p.remote.port))
            if key in seen:
                self.pruned += 1
                continue
            seen.add(key)
            pruned.append(p)
        self.pruned += max(0, len(pruned) - MAX_PAIRS)
        self.pairs = pruned[:MAX_PAIRS]
        # initial states: first pair per foundation Waiting, rest Frozen (6.1.2.6)
        first = set()
        for p in self.pairs:
            if p.foundation not in first:
                first.add(p.foundation)
                p.move("waiting")

    def next_pair(self) -> Pair | None:
        if self.triggered:
            return self.triggered.pop(0)
        for p in self.pairs:
            if p.state == "waiting":
                return p
        for p in self.pairs:  # unfreeze by foundation once nothing is waiting
            if p.state == "frozen":
                p.move("waiting")
                return p
        return None

    def run_checks(self, check, *, now: float = 0.0, budget: int = MAX_PAIRS * 2) -> Pair | None:
        """Drive checks until a pair succeeds and is nominated (controlling side) or budget ends."""
        steps = 0
        while steps < budget:
            p = self.next_pair()
            if p is None:
                break
            steps += 1
            if p.state == "failed":
                p.move("waiting")
            p.move("in-progress")
            try:
                ok = bool(check(p))
            except Exception:
                ok = False
            if ok:
                p.move("succeeded")
                p.last_response = now
                for q in self.pairs:     # unfreeze pairs sharing the foundation
                    if q.state == "frozen" and q.foundation == p.foundation:
                        q.move("waiting")
                if self.controlling:
                    p.nominated = True
                    self.selected = p
                    return p
            else:
                p.move("failed")
        return self.selected

    def on_incoming_check(self, source: tuple[str, int], local: Candidate, *, remote_controlling: bool,
                          remote_tie_breaker: int) -> str:
        """Handle a check from the peer: role conflict, prflx learning, triggered check."""
        if remote_controlling == self.controlling:
            if (self.tie_breaker >= remote_tie_breaker) == self.controlling:
                return "487-role-conflict"      # we keep our role; peer must switch
            self.controlling = not self.controlling
            for p in self.pairs:
                p.controlling = self.controlling
        known = next((c for c in self.remote if (c.ip, c.port) == tuple(source)), None)
        if known is None:
            known = Candidate("prflx", source[0], int(source[1]), component=local.component)
            if len(self.remote) < MAX_CANDIDATES:
                self.remote.append(known)
        pair = next((p for p in self.pairs if p.remote == known and p.local == local), None)
        if pair is None:
            if len(self.pairs) >= MAX_PAIRS:
                self.pruned += 1
                return "ignored-pair-ceiling"
            pair = Pair(local, known, self.controlling, state="waiting")
            self.pairs.append(pair)
        if pair.state in ("waiting", "frozen", "failed"):
            if pair.state == "frozen":
                pair.move("waiting")
            self.triggered.append(pair)
        return "triggered"

    def consent(self, now: float) -> bool:
        """RFC 7675: the selected pair loses consent CONSENT_TIMEOUT s after its last response."""
        if self.selected is None or self.selected.last_response is None:
            return False
        return 0 <= now - self.selected.last_response <= CONSENT_TIMEOUT

    def refresh_consent(self, now: float) -> None:
        if self.selected is not None:
            self.selected.last_response = now


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    best: dict[tuple, Candidate] = {}
    for c in cands:
        k = (c.ip, c.port, c.component)
        if k not in best or c.priority > best[k].priority:
            best[k] = c
    return list(best.values())
