"""Authentication (7), authorization policy (8), node identity and attestation
(18), signed artifact verification (19), rate limiting/backpressure (24).

Authentication model: each caller has a shared HMAC-SHA256 key provisioned
through :class:`config.SecretBoundary`.  A request is accepted only if its
signature covers (caller, request_id, nonce, ts, op, args), its timestamp is
within ``request_skew_s`` of the supervisor clock, and its nonce has not been
seen inside the replay window.  mTLS/SPIFFE transport identity is an
integration point (see ADR-0003) and is *not* claimed here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import pathlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from .config import canonical
from .errors import SupervisorError

# ---------------------------------------------------------------- authz (8)
CAPABILITIES = frozenset({
    "lifecycle.transition", "lifecycle.cordon", "lifecycle.uncordon", "drain.start",
    "drain.override", "health.report", "workload.admit", "workload.terminate",
    "emergency.enter", "emergency.exit", "emergency.disable", "state.read",
    "diagnostics.read", "config.reload",
})

OP_CAPABILITY = {
    "transition": "lifecycle.transition",
    "cordon": "lifecycle.cordon",
    "uncordon": "lifecycle.uncordon",
    "drain": "drain.start",
    "drain_override": "drain.override",
    "report_health": "health.report",
    "admit": "workload.admit",
    "terminate": "workload.terminate",
    "emergency_enter": "emergency.enter",
    "emergency_exit": "emergency.exit",
    "disable": "emergency.disable",
    "status": "state.read",
    "diagnostics": "diagnostics.read",
    "reload_config": "config.reload",
    "cordon_ack": "lifecycle.cordon",
    "control_plane_heartbeat": "lifecycle.transition",
}

DEFAULT_ROLES: dict[str, frozenset[str]] = {
    "control-plane": frozenset({"lifecycle.transition", "lifecycle.cordon", "lifecycle.uncordon",
                                "drain.start", "workload.admit", "state.read"}),
    "health-reporter": frozenset({"health.report"}),
    "runtime": frozenset({"health.report", "state.read"}),
    "operator": frozenset({"lifecycle.transition", "lifecycle.cordon", "lifecycle.uncordon",
                           "drain.start", "drain.override", "workload.terminate", "state.read",
                           "diagnostics.read", "emergency.enter", "emergency.exit",
                           "config.reload"}),
    "break-glass": frozenset({"emergency.enter", "emergency.disable", "workload.terminate",
                              "state.read", "diagnostics.read"}),
    "observer": frozenset({"state.read"}),
}


@dataclass
class Grant:
    capability: str
    expires_at: float
    reason: str


@dataclass
class AuthorizationPolicy:
    """Deny-by-default role->capability policy with expiring override grants."""
    bindings: dict[str, set[str]] = field(default_factory=dict)  # caller -> roles
    roles: dict[str, frozenset[str]] = field(default_factory=lambda: dict(DEFAULT_ROLES))
    overrides: dict[str, list[Grant]] = field(default_factory=dict)

    def bind(self, caller: str, *roles: str) -> None:
        for r in roles:
            if r not in self.roles:
                raise SupervisorError("E_CONFIG", f"unknown role {r!r}")
        self.bindings.setdefault(caller, set()).update(roles)

    def grant_override(self, caller: str, capability: str, *, ttl_s: float, reason: str,
                       now: float | None = None) -> Grant:
        if capability not in CAPABILITIES:
            raise SupervisorError("E_CONFIG", f"unknown capability {capability!r}")
        if not reason.strip() or ttl_s <= 0 or ttl_s > 3600:
            raise SupervisorError("E_BAD_REQUEST", "override requires reason and 0<ttl<=3600s")
        g = Grant(capability, (now if now is not None else time.time()) + ttl_s, reason.strip())
        self.overrides.setdefault(caller, []).append(g)
        return g

    def capabilities(self, caller: str, now: float | None = None) -> set[str]:
        now = time.time() if now is None else now
        caps: set[str] = set()
        for r in self.bindings.get(caller, ()):
            caps |= self.roles[r]
        live = [g for g in self.overrides.get(caller, []) if g.expires_at > now]
        self.overrides[caller] = live
        caps |= {g.capability for g in live}
        return caps

    def check(self, caller: str, op: str, now: float | None = None) -> str:
        cap = OP_CAPABILITY.get(op)
        if cap is None:
            raise SupervisorError("E_BAD_REQUEST", f"unknown operation {op!r}")
        if cap not in self.capabilities(caller, now):
            raise SupervisorError("E_FORBIDDEN", f"{caller} lacks {cap}")
        return cap


# ---------------------------------------------------------------- authn (7)
def sign_request(req: dict, key: bytes) -> str:
    body = {k: req.get(k) for k in ("caller", "request_id", "nonce", "ts", "op", "args")}
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


class Authenticator:
    def __init__(self, keys: dict[str, bytes], *, skew_s: float = 30, window: int = 4096) -> None:
        self._keys = dict(keys)
        self.skew_s = skew_s
        self.window = window
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def add_key(self, caller: str, key: bytes) -> None:
        if len(key) < 16:
            raise SupervisorError("E_CONFIG", "caller key shorter than 16 bytes")
        self._keys[caller] = key

    def authenticate(self, req: dict, now: float) -> str:
        caller = req.get("caller")
        key = self._keys.get(caller) if isinstance(caller, str) else None
        if key is None or not isinstance(caller, str):
            raise SupervisorError("E_UNAUTHENTICATED", "unknown caller")
        if not hmac.compare_digest(sign_request(req, key), str(req.get("sig", ""))):
            raise SupervisorError("E_UNAUTHENTICATED", "bad signature")
        ts = req.get("ts")
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or abs(now - ts) > self.skew_s:
            raise SupervisorError("E_STALE_REQUEST", "timestamp outside skew window")
        nonce = f"{caller}:{req.get('nonce')}"
        with self._lock:
            if nonce in self._seen:
                raise SupervisorError("E_REPLAY", "nonce reused")
            self._seen[nonce] = now
            while len(self._seen) > self.window:
                self._seen.popitem(last=False)
        return caller


# ---------------------------------------------------------- rate limit (24)
class RateLimiter:
    """Per-caller token bucket plus global in-flight ceiling."""

    def __init__(self, rate: float, burst: int, max_in_flight: int) -> None:
        self.rate, self.burst, self.max_in_flight = rate, burst, max_in_flight
        self._buckets: dict[str, tuple[float, float]] = {}
        self.in_flight = 0
        self._lock = threading.Lock()
        self.rejected = 0

    def acquire(self, caller: str, now: float) -> None:
        with self._lock:
            tokens, last = self._buckets.get(caller, (float(self.burst), now))
            tokens = min(self.burst, tokens + max(0.0, now - last) * self.rate)
            if tokens < 1 or self.in_flight >= self.max_in_flight:
                self._buckets[caller] = (tokens, now)
                self.rejected += 1
                raise SupervisorError("E_RATE_LIMITED", f"{caller} throttled")
            self._buckets[caller] = (tokens - 1, now)
            self.in_flight += 1

    def release(self) -> None:
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)


# ----------------------------------------------- identity/attestation (18)
@dataclass(frozen=True)
class NodeIdentity:
    node_id: str
    key: bytes = field(repr=False)

    def attest(self, measurements: dict, nonce: str) -> dict:
        """Produce a keyed attestation over boot measurements.  This is a
        software attestation (HMAC); TPM quote integration is an exception
        recorded in EXCEPTIONS.md (EXC-002)."""
        body = {"node_id": self.node_id, "nonce": nonce, "measurements": measurements}
        return {**body, "mac": hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()}

    def verify(self, att: dict) -> bool:
        body = {k: att.get(k) for k in ("node_id", "nonce", "measurements")}
        want = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
        return att.get("node_id") == self.node_id and hmac.compare_digest(want, str(att.get("mac", "")))


# --------------------------------------------- artifact verification (19)
def file_digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifacts(root: str | pathlib.Path, manifest_path: str | pathlib.Path,
                     key: bytes | None = None) -> list[str]:
    """Verify a ``{"files": {rel: sha256}, "signature": hmac}`` manifest.
    Returns a list of problems; empty means verified."""
    root = pathlib.Path(root)
    doc = json.loads(pathlib.Path(manifest_path).read_text())
    problems: list[str] = []
    files = doc.get("files", {})
    if key is not None:
        want = hmac.new(key, canonical(files), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, str(doc.get("signature", ""))):
            problems.append("manifest signature invalid")
    for rel, digest in sorted(files.items()):
        p = (root / rel).resolve()
        if root.resolve() not in p.parents and p != root.resolve():
            problems.append(f"{rel}: path escapes root")
        elif not p.is_file():
            problems.append(f"{rel}: missing")
        elif file_digest(p) != digest:
            problems.append(f"{rel}: digest mismatch")
    return problems
