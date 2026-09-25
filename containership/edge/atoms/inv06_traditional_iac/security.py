"""Identity, authorization, signing, redaction, tenancy and signed audit.

Package-local references for MC-033, MC-034, MC-036 (plan/artifact signing and
verification), MC-037, MC-039, MC-040 and MC-041.  Keys come from a
``KeyProvider``; ``StaticKeyProvider`` exists for tests and air-gapped
reference use only.  A production deployment binds ``KeyProvider`` to the
estate KMS/HSM (MC-038) — the package does not ship key custody.

Every decision here is default-deny and fail-closed: a missing key, an unknown
principal, an unavailable security dependency or an unsigned artefact refuses
the operation.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import pathlib
import re
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .state import IacError, _canonical_bytes


class AuthenticationFailed(IacError):
    code = "PK_IAC_AUTHN_FAILED"


class AccessDenied(IacError):
    code = "PK_IAC_ACCESS_DENIED"


class SignatureInvalid(IacError):
    code = "PK_IAC_SIGNATURE_INVALID"


class SecurityDependencyUnavailable(IacError):
    code = "PK_IAC_SECURITY_DEPENDENCY_UNAVAILABLE"


class TenantBoundaryViolation(IacError):
    code = "PK_IAC_TENANT_BOUNDARY"


# --------------------------------------------------------------------------- keys
class KeyProvider(Protocol):
    def key(self, key_id: str) -> bytes: ...
    def active_key_id(self, purpose: str) -> str: ...


class StaticKeyProvider:
    """In-memory key ring with rotation (retired keys verify, never sign)."""

    def __init__(self, keys: Mapping[str, bytes], active: Mapping[str, str]) -> None:
        for kid, k in keys.items():
            if len(k) < 32:
                raise SignatureInvalid("keys must be at least 256 bits", details={"key_id": kid})
        self._keys = dict(keys)
        self._active = dict(active)
        self._revoked: set[str] = set()

    def key(self, key_id: str) -> bytes:
        if key_id in self._revoked or key_id not in self._keys:
            raise SignatureInvalid("unknown or revoked key", details={"key_id": key_id})
        return self._keys[key_id]

    def active_key_id(self, purpose: str) -> str:
        try:
            return self._active[purpose]
        except KeyError as exc:
            raise SecurityDependencyUnavailable("no active key for purpose", details={"purpose": purpose}) from exc

    def rotate(self, purpose: str, key_id: str, key: bytes) -> None:
        if len(key) < 32:
            raise SignatureInvalid("keys must be at least 256 bits")
        self._keys[key_id] = key
        self._active[purpose] = key_id

    def revoke(self, key_id: str) -> None:
        self._revoked.add(key_id)


# ------------------------------------------------------------------ signatures
class Signer:
    """HMAC-SHA256 envelope signer for plans, evidence and artefact manifests."""

    ALG = "HMAC-SHA256"

    def __init__(self, keys: KeyProvider, purpose: str) -> None:
        self.keys, self.purpose = keys, purpose

    def sign(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        kid = self.keys.active_key_id(self.purpose)
        mac = hmac.new(self.keys.key(kid), _canonical_bytes({"purpose": self.purpose, "payload": payload}), hashlib.sha256).hexdigest()
        return {"alg": self.ALG, "key_id": kid, "purpose": self.purpose, "mac": mac}

    def verify(self, payload: Mapping[str, Any], sig: Mapping[str, Any]) -> None:
        if not isinstance(sig, Mapping) or sig.get("alg") != self.ALG or sig.get("purpose") != self.purpose:
            raise SignatureInvalid("signature envelope missing or wrong purpose")
        key = self.keys.key(str(sig.get("key_id")))
        want = hmac.new(key, _canonical_bytes({"purpose": self.purpose, "payload": payload}), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, str(sig.get("mac", ""))):
            raise SignatureInvalid("signature verification failed", details={"key_id": sig.get("key_id")})


def sign_plan(plan: Mapping[str, Any], signer: Signer, *, approver: str) -> dict[str, Any]:
    out = dict(plan)
    out.pop("authorization", None)
    body = {"plan_digest": plan["integrity"]["digest"], "serial": plan["serial"], "approver": approver}
    out["authorization"] = {**body, "signature": signer.sign(body)}
    return out


def verify_signed_plan(plan: Mapping[str, Any], signer: Signer) -> dict[str, Any]:
    auth = plan.get("authorization")
    if not isinstance(auth, Mapping):
        raise SignatureInvalid("plan is not signed")
    body = {k: auth.get(k) for k in ("plan_digest", "serial", "approver")}
    signer.verify(body, auth.get("signature", {}))
    if body["plan_digest"] != plan.get("integrity", {}).get("digest") or body["serial"] != plan.get("serial"):
        raise SignatureInvalid("signature does not bind this plan")
    return {k: v for k, v in plan.items() if k != "authorization"}


def verify_artifact(path: str | os.PathLike[str], *, expected_sha256: str, allowlist: Mapping[str, str] | None = None, name: str | None = None) -> str:
    """Verify a binary/provider artefact digest and optional allowlist pin (MC-036/MC-018)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    got = h.hexdigest()
    if not hmac.compare_digest(got, expected_sha256.lower()):
        raise SignatureInvalid("artifact digest mismatch", details={"path": str(path), "expected": expected_sha256, "actual": got})
    if allowlist is not None:
        if name not in allowlist or allowlist[name].lower() != got:
            raise SignatureInvalid("artifact not on allowlist", details={"name": name})
    return got


# ---------------------------------------------------------------- authn/authz
@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str  # operator | workload | service | node
    tenant: str
    roles: frozenset[str] = field(default_factory=frozenset)


class TokenAuthenticator:
    """Verifies compact HMAC bearer tokens: ``b64(claims).mac``.

    Claims: ``sub``, ``kind``, ``tenant``, ``roles``, ``exp``, ``aud``.  A
    production deployment replaces this with OIDC/mTLS/SPIFFE verification
    behind the same ``authenticate()`` signature.
    """

    KINDS = {"operator", "workload", "service", "node"}

    def __init__(self, keys: KeyProvider, audience: str, *, clock: Callable[[], float] = time.time, max_ttl: float = 3600) -> None:
        self.signer = Signer(keys, "authn")
        self.audience, self.clock, self.max_ttl = audience, clock, max_ttl

    def issue(self, sub: str, kind: str, tenant: str, roles: list[str], ttl: float = 900) -> str:
        claims = {"sub": sub, "kind": kind, "tenant": tenant, "roles": sorted(roles), "exp": self.clock() + min(ttl, self.max_ttl), "aud": self.audience}
        sig = self.signer.sign(claims)
        blob = base64.urlsafe_b64encode(_canonical_bytes({"claims": claims, "sig": sig})).decode()
        return blob

    def authenticate(self, token: str | None) -> Principal:
        if not token or len(token) > 8192:
            raise AuthenticationFailed("missing or oversized credential")
        try:
            env = json.loads(base64.urlsafe_b64decode(token.encode()))
            claims, sig = env["claims"], env["sig"]
        except Exception as exc:  # noqa: BLE001 - any decode failure is an auth failure
            raise AuthenticationFailed("malformed credential") from exc
        try:
            self.signer.verify(claims, sig)
        except SignatureInvalid as exc:
            raise AuthenticationFailed("credential signature invalid") from exc
        if claims.get("aud") != self.audience:
            raise AuthenticationFailed("wrong audience")
        if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] <= self.clock():
            raise AuthenticationFailed("credential expired")
        if claims.get("kind") not in self.KINDS:
            raise AuthenticationFailed("unknown principal kind")
        return Principal(claims["sub"], claims["kind"], claims["tenant"], frozenset(claims.get("roles", [])))


ACTIONS = (
    "state.read", "plan.create", "plan.approve", "apply", "protect", "unprotect",
    "state.import", "state.export", "state.rollback", "emergency.freeze", "emergency.unfreeze", "drift.scan",
)

DEFAULT_ROLES: dict[str, frozenset[str]] = {
    "viewer": frozenset({"state.read", "drift.scan"}),
    "planner": frozenset({"state.read", "drift.scan", "plan.create"}),
    "approver": frozenset({"state.read", "plan.approve"}),
    "applier": frozenset({"state.read", "apply"}),
    "custodian": frozenset({"state.read", "protect", "unprotect", "state.export"}),
    "recovery": frozenset({"state.read", "state.rollback", "state.import"}),
    "incident-commander": frozenset({"state.read", "emergency.freeze", "emergency.unfreeze"}),
}


class Authorizer:
    """Default-deny role → capability engine with tenant scoping and separation of duties."""

    def __init__(self, roles: Mapping[str, frozenset[str]] = DEFAULT_ROLES) -> None:
        for r, caps in roles.items():
            bad = set(caps) - set(ACTIONS)
            if bad:
                raise AccessDenied("role grants unknown action", details={"role": r, "actions": sorted(bad)})
        self.roles = dict(roles)

    def check(self, principal: Principal, action: str, *, tenant: str) -> None:
        if action not in ACTIONS:
            raise AccessDenied("unknown action", details={"action": action})
        if principal.tenant != tenant:
            raise TenantBoundaryViolation("cross-tenant access refused", details={"principal_tenant": principal.tenant, "tenant": tenant})
        caps = set().union(*(self.roles.get(r, frozenset()) for r in principal.roles)) if principal.roles else set()
        if action not in caps:
            raise AccessDenied("action not permitted", details={"subject": principal.subject, "action": action})

    @staticmethod
    def separation_of_duties(planner: str, approver: str, applier: str | None = None) -> None:
        if planner == approver:
            raise AccessDenied("plan author may not approve their own plan", details={"subject": planner})


# ------------------------------------------------------------------ redaction
SENSITIVE_KEY = re.compile(r"(pass(word)?|secret|token|api[_-]?key|private[_-]?key|credential|auth|session|cookie|connection[_-]?string)", re.I)
SENSITIVE_VALUE = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)\b[a-z]+://[^/\s:@]+:[^/\s@]+@"),
]
REDACTED = "***REDACTED***"


def redact(value: Any, *, _key: str | None = None) -> Any:
    """Return a copy with sensitive keys/values replaced.  Safe for logs, traces, fixtures, diagnostics."""
    if _key is not None and SENSITIVE_KEY.search(_key):
        return REDACTED
    if isinstance(value, Mapping):
        return {k: redact(v, _key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str) and any(p.search(value) for p in SENSITIVE_VALUE):
        return REDACTED
    return value


def contains_secret(value: Any) -> bool:
    return redact(value) != value


# ------------------------------------------------------------------- tenancy
class TenantRegistry:
    """Per-tenant isolated state namespaces with quotas (MC-037)."""

    NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

    def __init__(self, root: str | os.PathLike[str], *, max_resources: int = 10_000) -> None:
        self.root = pathlib.Path(root)
        self.max_resources = max_resources
        self._lock = threading.Lock()
        self._backends: dict[str, Any] = {}

    def backend(self, tenant: str) -> Any:
        from .durable import FileStateBackend

        if not self.NAME.match(tenant or ""):
            raise TenantBoundaryViolation("invalid tenant identifier", details={"tenant": tenant})
        with self._lock:
            if tenant not in self._backends:
                path = (self.root / tenant).resolve()
                if self.root.resolve() not in path.parents:
                    raise TenantBoundaryViolation("tenant path escapes root")
                self._backends[tenant] = FileStateBackend(path)
            return self._backends[tenant]

    def enforce_quota(self, tenant: str, desired: Mapping[str, Any]) -> None:
        if len(desired) > self.max_resources:
            raise TenantBoundaryViolation("tenant resource quota exceeded", details={"tenant": tenant, "count": len(desired), "limit": self.max_resources})


# --------------------------------------------------------- security outages
OUTAGE_POLICY: dict[str, dict[str, str]] = {
    # dependency: {operation-class: behaviour}
    "identity": {"mutate": "deny", "read": "deny", "emergency": "deny"},
    "policy": {"mutate": "deny", "read": "allow", "emergency": "allow-freeze-only"},
    "keys": {"mutate": "deny", "read": "allow", "emergency": "allow-freeze-only"},
    "audit": {"mutate": "deny", "read": "allow", "emergency": "allow-freeze-only"},
    "time": {"mutate": "deny", "read": "allow", "emergency": "allow-freeze-only"},
    "attestation": {"mutate": "deny", "read": "allow", "emergency": "allow-freeze-only"},
}


def outage_decision(unavailable: set[str], op_class: str, action: str = "") -> None:
    """Raise unless every unavailable security dependency permits ``op_class`` (MC-039)."""
    for dep in sorted(unavailable):
        rule = OUTAGE_POLICY.get(dep, {}).get(op_class, "deny")
        if rule == "allow":
            continue
        if rule == "allow-freeze-only" and action == "emergency.freeze":
            continue
        raise SecurityDependencyUnavailable("security dependency unavailable; failing closed", details={"dependency": dep, "op_class": op_class, "action": action})


# ------------------------------------------------------------ signed audit
class SignedAuditLog:
    """Append-only, hash-chained, HMAC-signed JSONL audit sink (MC-040 reference).

    Durable on local disk with fsync per event.  Retention/WORM storage,
    trusted third-party timestamps and export to the estate SIEM are the
    deployment's responsibility; ``export()`` provides the verifiable bundle.
    """

    def __init__(self, path: str | os.PathLike[str], signer: Signer) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.signer = signer
        self._lock = threading.Lock()

    def _tail(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, "0" * 64
        last = None
        with open(self.path, "rb") as fh:
            for line in fh:
                if line.strip():
                    last = line
        if last is None:
            return 0, "0" * 64
        e = json.loads(last)
        return e["seq"], e["digest"]

    def append(self, action: str, actor: str, details: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            seq, prev = self._tail()
            body = {"seq": seq + 1, "time_ns": time.time_ns(), "action": action, "actor": actor, "details": redact(dict(details)), "previous_digest": prev}
            body["digest"] = hashlib.sha256(_canonical_bytes(body)).hexdigest()
            body["signature"] = self.signer.sign({"digest": body["digest"]})
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(body, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return body

    def verify(self) -> int:
        prev, n = "0" * 64, 0
        if not self.path.exists():
            return 0
        for raw in self.path.read_text("utf-8").splitlines():
            if not raw.strip():
                continue
            e = json.loads(raw)
            sig = e.pop("signature")
            digest = e.pop("digest")
            if e["previous_digest"] != prev or e["seq"] != n + 1:
                raise SignatureInvalid("audit chain broken", details={"seq": e.get("seq")})
            if hashlib.sha256(_canonical_bytes(e)).hexdigest() != digest:
                raise SignatureInvalid("audit event digest mismatch", details={"seq": e["seq"]})
            self.signer.verify({"digest": digest}, sig)
            prev, n = digest, n + 1
        return n

    def export(self) -> dict[str, Any]:
        count = self.verify()
        data = self.path.read_bytes() if self.path.exists() else b""
        return {"schema": "PK_IAC_AUDIT_EXPORT/1", "events": count, "sha256": hashlib.sha256(data).hexdigest(), "head": self._tail()[1]}
