"""MC-19 authentication, MC-20 authorization, MC-24 secret provider, MC-25 attestation.

Mechanism only.  No real principal, key, KMS or hardware root of trust is bound in this
archive: the keys used by tests are generated per test run and never shipped.  Every
path fails closed: a missing key, an unknown principal, an expired or replayed credential,
or evidence that does not verify is a refusal, never a pass.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from .errors import SchedulerError


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


# ---------------------------------------------------------------- MC-24 secrets
class SecretProvider(Protocol):
    def get(self, key_id: str) -> bytes: ...


class StaticSecretProvider:
    """In-memory provider with rotation.  A production binding (KMS/HSM) is EXT work."""

    def __init__(self, keys: Mapping[str, bytes] | None = None, *, available: bool = True):
        self._keys = dict(keys or {})
        self._retired: set[str] = set()
        self.available = available
        self._lock = threading.Lock()

    def get(self, key_id: str) -> bytes:
        with self._lock:
            if not self.available:
                raise SchedulerError("SECRET_UNAVAILABLE", "secret provider unavailable")
            if key_id in self._retired or key_id not in self._keys:
                raise SchedulerError("SECRET_UNAVAILABLE", f"key {key_id!r} unavailable or retired")
            k = self._keys[key_id]
            if not isinstance(k, bytes) or len(k) < 32:
                raise SchedulerError("SECRET_UNAVAILABLE", "key material below 256 bits")
            return k

    def rotate(self, key_id: str, new_key: bytes, *, retire: str | None = None) -> None:
        with self._lock:
            self._keys[key_id] = new_key
            if retire:
                self._retired.add(retire)

    def __repr__(self) -> str:  # never print key material
        return f"StaticSecretProvider(keys={sorted(self._keys)}, available={self.available})"


def mac(provider: SecretProvider, key_id: str, payload: Any) -> str:
    return hmac.new(provider.get(key_id), canonical(payload), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------- MC-19 authn
@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str          # human | service | node
    tenants: frozenset[str]
    roles: frozenset[str]


class Authenticator:
    """HMAC bearer tokens with audience, expiry, and nonce anti-replay."""

    def __init__(self, secrets: SecretProvider, *, audience: str = "sch-01", key_id: str = "authn",
                 clock: Callable[[], int] = lambda: 0, max_ttl: int = 300):
        self.secrets, self.audience, self.key_id, self.clock, self.max_ttl = secrets, audience, key_id, clock, max_ttl
        self._seen: dict[str, int] = {}
        self._lock = threading.Lock()

    def issue(self, principal: Principal, *, nonce: str, ttl: int = 60) -> dict[str, Any]:
        body = {"sub": principal.subject, "kind": principal.kind, "tenants": sorted(principal.tenants),
                "roles": sorted(principal.roles), "aud": self.audience, "iat": self.clock(),
                "exp": self.clock() + min(ttl, self.max_ttl), "nonce": nonce, "kid": self.key_id}
        return {"body": body, "mac": mac(self.secrets, self.key_id, body)}

    def authenticate(self, token: Mapping[str, Any] | None) -> Principal:
        try:
            body, sig = dict(token["body"]), str(token["mac"])  # type: ignore[index]
        except Exception:
            raise SchedulerError("UNAUTHENTICATED", "missing or malformed credential") from None
        kid = body.get("kid")
        if kid != self.key_id:
            raise SchedulerError("UNAUTHENTICATED", "unknown key id")
        expect = mac(self.secrets, kid, body)
        if not hmac.compare_digest(expect, sig):
            raise SchedulerError("UNAUTHENTICATED", "credential signature invalid")
        now = self.clock()
        if body.get("aud") != self.audience:
            raise SchedulerError("UNAUTHENTICATED", "wrong audience")
        if not isinstance(body.get("exp"), int) or now >= body["exp"] or body.get("iat", now + 1) > now:
            raise SchedulerError("UNAUTHENTICATED", "credential expired or not yet valid")
        if body["exp"] - body["iat"] > self.max_ttl:
            raise SchedulerError("UNAUTHENTICATED", "credential lifetime exceeds policy")
        nonce = body.get("nonce")
        with self._lock:
            self._seen = {n: e for n, e in self._seen.items() if e > now}
            if not nonce or nonce in self._seen:
                raise SchedulerError("UNAUTHENTICATED", "credential replayed")
            self._seen[nonce] = body["exp"]
        if body.get("kind") not in ("human", "service", "node"):
            raise SchedulerError("UNAUTHENTICATED", "unknown principal kind")
        return Principal(body["sub"], body["kind"], frozenset(body["tenants"]), frozenset(body["roles"]))


# ---------------------------------------------------------------- MC-20 authz
PERMISSIONS: dict[str, frozenset[str]] = {
    "placement.request": frozenset({"workload-submitter"}),
    "placement.release": frozenset({"workload-submitter", "execution-plane"}),
    "placement.explain": frozenset({"workload-submitter", "operator", "auditor"}),
    "node.report": frozenset({"node-agent"}),
    "admin.freeze": frozenset({"operator"}),
    "admin.disable": frozenset({"operator"}),
    "admin.quarantine": frozenset({"operator"}),
    "config.activate": frozenset({"config-admin"}),
    "policy.activate": frozenset({"policy-admin"}),
    "audit.read": frozenset({"auditor"}),
}
ADMIN_OPS = {op for op in PERMISSIONS if op.startswith(("admin.", "config.", "policy."))}


def authorize(principal: Principal, operation: str, tenant: str | None = None) -> None:
    allowed = PERMISSIONS.get(operation)
    if allowed is None:
        raise SchedulerError("FORBIDDEN", f"unknown operation {operation!r}")
    if not (principal.roles & allowed):
        raise SchedulerError("FORBIDDEN", f"{principal.subject} lacks capability for {operation}")
    if operation in ADMIN_OPS and principal.kind == "node":
        raise SchedulerError("FORBIDDEN", "node identities cannot perform administrative operations")
    if tenant is not None and tenant not in principal.tenants and "*" not in principal.tenants:
        raise SchedulerError("FORBIDDEN", "principal not authorized for this tenant")


# ---------------------------------------------------------------- MC-25 attestation
class AttestationVerifier:
    """Verifies node evidence: signer key, node identity binding, measurement allow-list,
    freshness and anti-replay.  The signer here is HMAC with a provider key; a TPM/SEV/TDX
    quote verifier is the EXT-04 binding and is not present."""

    def __init__(self, secrets: SecretProvider, *, allowed_measurements: Mapping[str, frozenset[str]],
                 key_id: str = "attest", max_age: int = 60):
        self.secrets, self.allowed, self.key_id, self.max_age = secrets, dict(allowed_measurements), key_id, max_age
        self._counters: dict[str, int] = {}
        self._lock = threading.Lock()

    def sign(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        return {"evidence": dict(evidence), "mac": mac(self.secrets, self.key_id, dict(evidence))}

    def verify(self, node_name: str, tiers: frozenset[str], signed: Mapping[str, Any] | None, now: int) -> frozenset[str]:
        """Return the set of tiers the evidence proves; raise on any failure."""
        if not signed:
            raise SchedulerError("ATTESTATION_FAILED", "no attestation evidence", details={"node": node_name})
        ev = dict(signed.get("evidence") or {})
        if not hmac.compare_digest(mac(self.secrets, self.key_id, ev), str(signed.get("mac", ""))):
            raise SchedulerError("ATTESTATION_FAILED", "evidence signature invalid", details={"node": node_name})
        if ev.get("node") != node_name:
            raise SchedulerError("ATTESTATION_FAILED", "evidence bound to a different node", details={"node": node_name})
        at = ev.get("at")
        if not isinstance(at, int) or at > now or now - at > self.max_age:
            raise SchedulerError("ATTESTATION_FAILED", "evidence stale or from the future", details={"node": node_name})
        ctr = ev.get("counter")
        with self._lock:
            if not isinstance(ctr, int) or ctr <= self._counters.get(node_name, -1):
                raise SchedulerError("ATTESTATION_FAILED", "evidence replayed (counter did not advance)",
                                     details={"node": node_name})
            self._counters[node_name] = ctr
        proven = set()
        for tier, meas in dict(ev.get("measurements") or {}).items():
            if tier in tiers and meas in self.allowed.get(tier, frozenset()):
                proven.add(tier)
        return frozenset(proven)
