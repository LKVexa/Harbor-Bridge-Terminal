"""Adjacent-layer adapters (GAP04-C09..C13).

Each adapter is a typing.Protocol with an explicit ``CONTRACT`` identifier and
a ``negotiate`` guard (unsupported contract -> E0901). A reference in-process
implementation is supplied for every protocol; they are complete enough to run
the integration suite and to act as executable contract specifications for the
real GAP-01/05/12/13/PLN-07 implementations, which live outside this package.
"""
from __future__ import annotations

import secrets
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from . import canonical, crypto
from .errors import AdapterError, Fenced, Gap04Error
from .fencing import FencingValidator
from .trust import TrustStore, VerifiedPolicy

CONTRACTS = {
    "GAP-12": "PK_REACHABILITY/1",
    "GAP-13": "PK_POLICY_ENGINE/1",
    "PLN-07": "PK_CAPABILITY/1",
    "GAP-01": "PK_SUPERVISOR_COMMAND/1",
    "GAP-05": "PK_REPLICATION_BATCH/1",
}


def negotiate(layer: str, offered: str) -> None:
    if CONTRACTS.get(layer) != offered:
        raise Gap04Error(f"{layer} contract {offered!r} unsupported", code="GAP04-E0901",
                         details={"layer": layer, "offered": offered, "supported": CONTRACTS.get(layer)})


# ---------------------------------------------------------------- GAP-12 reachability
HEARTBEAT_VERSION = "PK_HEARTBEAT/1"


class ReachabilityMonitor:
    """Authenticated, hysteretic, flap-aware reachability (C10).

    The control plane answers a nonce challenge with a signed heartbeat; an
    unsigned, unverifiable, replayed, or wrong-site heartbeat counts as a failed
    probe (spoof resistance). State moves to ``up`` only after ``up_after``
    consecutive verified probes and to ``down`` after ``down_after`` failures.
    More than ``flap_threshold`` transitions inside ``flap_window_s`` forces
    ``flapping``, which the node treats as partitioned. The initial state is
    ``unknown``: neither reachable (no renewals) nor partitioned (no autonomy). ``degraded`` = verified
    but high-latency/lossy link; it permits renewal but not bulk reconciliation.
    """
    CONTRACT = CONTRACTS["GAP-12"]

    def __init__(self, site: str, trust: TrustStore, *, up_after=3, down_after=2, flap_window_s=300,
                 flap_threshold=6, degraded_latency_ms=2000):
        self.site, self.trust = site, trust
        self.up_after, self.down_after = up_after, down_after
        self.flap_window, self.flap_threshold = flap_window_s, flap_threshold
        self.degraded_ms = degraded_latency_ms
        self.state = "unknown"
        self._ok = self._fail = 0
        self._transitions: deque[int] = deque()
        self._nonce: str | None = None
        self._lock = threading.Lock()

    def challenge(self) -> str:
        self._nonce = secrets.token_hex(16)
        return self._nonce

    def _verify(self, hb: Mapping[str, Any] | None, now: int) -> bool:
        if not hb or hb.get("version") != HEARTBEAT_VERSION or hb.get("site") != self.site:
            return False
        if self._nonce is None or hb.get("nonce") != self._nonce:
            return False
        try:
            key = self.trust.resolve(hb["key_id"], hb["issuer"], hb["alg"], "heartbeat", now)
        except Exception:
            return False
        body = {k: v for k, v in hb.items() if k != "sig"}
        return crypto.verify(key.public_key, canonical.dumps(body), hb.get("sig", ""))

    def observe(self, heartbeat: Mapping[str, Any] | None, now: int, latency_ms: int = 0) -> str:
        with self._lock:
            ok = self._verify(heartbeat, now)
            self._nonce = None
            if ok:
                self._ok, self._fail = self._ok + 1, 0
            else:
                self._fail, self._ok = self._fail + 1, 0
            prev = self.state
            new = prev
            if prev in ("down", "flapping", "unknown") and self._ok >= self.up_after:
                new = "up"
            elif prev in ("up", "degraded", "unknown") and self._fail >= self.down_after:
                new = "down"
            if new in ("up", "degraded") and ok:
                new = "degraded" if latency_ms >= self.degraded_ms else "up"
            while self._transitions and self._transitions[0] < now - self.flap_window:
                self._transitions.popleft()
            if (new in ("up", "degraded")) != (prev in ("up", "degraded")):
                self._transitions.append(now)
            if len(self._transitions) >= self.flap_threshold:
                new = "flapping"
            self.state = new
            return new

    @property
    def reachable(self) -> bool:
        return self.state in ("up", "degraded")


def sign_heartbeat(site: str, nonce: str, now: int, issuer: str, key_id: str, seed: bytes) -> dict:
    body = {"version": HEARTBEAT_VERSION, "site": site, "nonce": nonce, "time": now, "issuer": issuer,
            "key_id": key_id, "alg": "Ed25519"}
    return dict(body, sig=crypto.sign(seed, canonical.dumps(body)))


# ---------------------------------------------------------------- GAP-13 policy engine
class PolicyEngine(Protocol):
    CONTRACT: str
    def fetch(self) -> Mapping[str, Any]: ...
    def evaluate(self, policy: VerifiedPolicy, kind: str, subject: str, tier: str) -> tuple[bool, str]: ...


class ReferencePolicyEngine:
    """Evaluates PK_POLICY_BUNDLE/1 rules: {allow_kinds:[..], deny_subject_prefixes:[..],
    freeze_kinds:[..]} (freeze_kinds = kinds still allowed at freeze)."""
    CONTRACT = CONTRACTS["GAP-13"]

    def __init__(self, source: Callable[[], Mapping[str, Any]] | None = None):
        self._source = source

    def fetch(self) -> Mapping[str, Any]:
        if self._source is None:
            raise AdapterError("no policy source", details={"layer": "GAP-13"})
        return self._source()

    def evaluate(self, policy: VerifiedPolicy, kind: str, subject: str, tier: str) -> tuple[bool, str]:
        r = policy.rules
        if kind not in r.get("allow_kinds", []):
            return False, "policy:kind_not_allowed"
        if any(subject.startswith(p) for p in r.get("deny_subject_prefixes", [])):
            return False, "policy:subject_denied"
        if tier == "freeze" and kind not in r.get("freeze_kinds", ["restart"]):
            return False, "policy:not_allowed_at_freeze"
        return True, f"policy:v{policy.policy_version}"


# ---------------------------------------------------------------- PLN-07 capabilities
GRANT_VERSION = "PK_CAPABILITY_GRANT/1"


@dataclass
class CapabilityPlane:
    """Least-privilege capability evaluation from signed grants with revocation (C12)."""
    trust: TrustStore
    site: str
    CONTRACT: str = CONTRACTS["PLN-07"]
    grants: dict[str, dict] = field(default_factory=dict)
    revoked: set[str] = field(default_factory=set)
    revocation_epoch: int = 0

    def install_grant(self, grant: Mapping[str, Any], now: int) -> None:
        if grant.get("version") != GRANT_VERSION or grant.get("site") != self.site:
            raise Gap04Error("grant malformed or wrong site", code="GAP04-E0105")
        key = self.trust.resolve(grant["key_id"], grant["issuer"], grant["alg"], "grant", now)
        body = {k: v for k, v in grant.items() if k != "sig"}
        if not crypto.verify(key.public_key, canonical.dumps(body), grant.get("sig", "")):
            raise Gap04Error("grant signature invalid", code="GAP04-E0105")
        if grant["epoch"] < self.revocation_epoch:
            raise Gap04Error("grant predates revocation epoch", code="GAP04-E0105")
        self.grants[grant["grant_id"]] = dict(grant)

    def apply_revocations(self, epoch: int, revoked_ids: set[str]) -> None:
        if epoch < self.revocation_epoch:
            raise Gap04Error("revocation epoch regression", code="GAP04-E0206")
        self.revocation_epoch = epoch
        self.revoked |= set(revoked_ids)
        for gid in list(self.grants):
            if gid in self.revoked or self.grants[gid]["epoch"] < epoch:
                del self.grants[gid]

    def check(self, principal: str, capability: str, now: int) -> str:
        for gid, g in self.grants.items():
            if gid in self.revoked or g["principal"] != principal:
                continue
            if capability in g["capabilities"] and g["not_before"] <= now < g["expires_at"]:
                return gid
        raise Gap04Error("no valid capability grant", code="GAP04-E0105",
                         details={"principal": principal, "capability": capability})


def sign_grant(grant_id, site, principal, capabilities, epoch, nbf, exp, issuer, key_id, seed) -> dict:
    body = {"version": GRANT_VERSION, "grant_id": grant_id, "site": site, "principal": principal,
            "capabilities": sorted(capabilities), "epoch": epoch, "not_before": nbf, "expires_at": exp,
            "issuer": issuer, "key_id": key_id, "alg": "Ed25519"}
    return dict(body, sig=crypto.sign(seed, canonical.dumps(body)))


# ---------------------------------------------------------------- GAP-01 supervisor
class Supervisor(Protocol):
    CONTRACT: str
    def execute(self, command: Mapping[str, Any]) -> dict: ...
    def compensate(self, command_id: str) -> dict: ...


class ReferenceSupervisor:
    """Executes commands idempotently by command_id and rejects stale fencing tokens (C13, C16)."""
    CONTRACT = CONTRACTS["GAP-01"]

    def __init__(self, fail: Callable[[Mapping[str, Any]], bool] | None = None):
        self.fence = FencingValidator()
        self.executed: dict[str, dict] = {}
        self.workloads: dict[str, str] = {}
        self._fail = fail or (lambda c: False)
        self._lock = threading.Lock()

    def execute(self, command: Mapping[str, Any]) -> dict:
        negotiate("GAP-01", command.get("contract", ""))
        self.fence.admit(command["authority_epoch"], command["generation"])
        with self._lock:
            if command["command_id"] in self.executed:
                return dict(self.executed[command["command_id"]], replayed=True)
            if self._fail(command):
                raise AdapterError("supervisor rejected command", details={"layer": "GAP-01"})
            self.workloads[command["subject"]] = command["kind"]
            res = {"command_id": command["command_id"], "status": "applied", "replayed": False}
            self.executed[command["command_id"]] = res
            return res

    def compensate(self, command_id: str) -> dict:
        with self._lock:
            res = self.executed.get(command_id)
            if res is None:
                return {"command_id": command_id, "status": "unknown"}
            res["status"] = "compensated"
            return dict(res)


# ---------------------------------------------------------------- GAP-05 replication
class Replication(Protocol):
    CONTRACT: str
    def submit(self, batch: Mapping[str, Any]) -> dict: ...


class ReferenceReplication:
    """Authoritative side of reconnect reconciliation (C09).

    Applies decisions idempotently by decision_id, detects conflicts against
    authoritative state (an authoritative write on the same subject at/after the
    partition start), and returns a signed-by-construction ack token per batch.
    """
    CONTRACT = CONTRACTS["GAP-05"]

    def __init__(self, authoritative: dict[str, dict] | None = None, fail_times: int = 0):
        self.authoritative = authoritative or {}
        self.applied: dict[str, dict] = {}
        self.txns: dict[str, dict] = {}
        self.fail_times = fail_times
        self.calls = 0
        self._lock = threading.Lock()

    def submit(self, batch: Mapping[str, Any]) -> dict:
        with self._lock:
            return self._submit(batch)

    def _submit(self, batch: Mapping[str, Any]) -> dict:
        negotiate("GAP-05", batch.get("contract", ""))
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise AdapterError("replication peer unavailable", details={"layer": "GAP-05"})
        key = f"{batch['txn_id']}:{batch['batch_no']}"
        if key in self.txns:
            return self.txns[key]
        outcomes = []
        for d in batch["decisions"]:
            did = d["decision_id"]
            if did in self.applied:
                outcomes.append({"decision_id": did, "outcome": self.applied[did]["outcome"], "replayed": True})
                continue
            auth = self.authoritative.get(d["subject"])
            if auth and auth["at"] >= batch["partitioned_since"]:
                o = "conflict"
            else:
                o = "accepted"
                self.authoritative[d["subject"]] = {"kind": d["kind"], "at": d["at"], "by": "site"}
            self.applied[did] = {"outcome": o}
            outcomes.append({"decision_id": did, "outcome": o, "replayed": False})
        res = {"txn_id": batch["txn_id"], "batch_no": batch["batch_no"], "outcomes": outcomes,
               "ack": canonical.digest({"txn": batch["txn_id"], "b": batch["batch_no"], "o": outcomes})}
        self.txns[key] = res
        return res
