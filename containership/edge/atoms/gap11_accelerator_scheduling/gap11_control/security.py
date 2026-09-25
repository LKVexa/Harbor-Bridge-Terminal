"""Security boundary: GAP11-P0-09 device attestation binding, P0-10 authenticated
service boundary, P0-11 authorization/capability policy, P1-30 secrets/KMS.

Mechanisms are real (HMAC-SHA256 over canonical JSON, keyrings with rotation,
nonce replay cache, deny-by-default policy) but the *trust anchors* are local:
there is no GAP-06 attestation service, no mTLS PKI/SPIFFE issuer and no KMS in
this environment. Checks that require those external systems are BLOCKED in the
traceability matrix; the local keyring is a stand-in, never claimed as one.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from .common import ControlError, Telemetry, canonical

# ------------------------------------------------------------------ keyring + secrets (P1-30)
class SecretProvider:
    """Resolves ``secretref://name`` references. A KMS client plugs in as ``backend``."""

    def __init__(self, backend: Callable[[str], bytes] | None = None) -> None:
        self.backend = backend
        self._local: dict[str, bytes] = {}

    def put_local(self, name: str, value: bytes) -> str:
        self._local[name] = value
        return f"secretref://{name}"

    def resolve(self, ref: str) -> bytes:
        if not isinstance(ref, str) or not ref.startswith("secretref://"):
            raise ControlError("CONFIG_INVALID", "secrets must be referenced, never inlined")
        name = ref[len("secretref://"):]
        if self.backend is not None:
            try:
                return self.backend(name)
            except Exception as exc:  # KMS outage -> fail closed
                raise ControlError("DEPENDENCY_UNAVAILABLE", "secret backend unavailable") from exc
        if name not in self._local:
            raise ControlError("DEPENDENCY_UNAVAILABLE", "secret not found")
        return self._local[name]


class Keyring:
    """kid -> key, with an active signing kid. Rotation is live (no restart)."""

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}
        self._retired: set[str] = set()
        self.active: str | None = None
        self._lock = threading.Lock()

    def add(self, kid: str, key: bytes, *, activate: bool = False) -> None:
        if len(key) < 32:
            raise ControlError("CONFIG_INVALID", "keys must be >= 256 bits")
        with self._lock:
            self._keys[kid] = key
            if activate or self.active is None:
                self.active = kid

    def retire(self, kid: str) -> None:
        with self._lock:
            self._retired.add(kid)
            if self.active == kid:
                self.active = None

    def get(self, kid: str) -> bytes:
        with self._lock:
            if kid in self._retired or kid not in self._keys:
                raise ControlError("UNAUTHENTICATED", "unknown or retired key id")
            return self._keys[kid]


def sign(keyring: Keyring, claims: dict[str, Any]) -> dict[str, Any]:
    if keyring.active is None:
        raise ControlError("DEPENDENCY_UNAVAILABLE", "no active signing key")
    mac = hmac.new(keyring.get(keyring.active), canonical(claims), hashlib.sha256).hexdigest()
    return {"kid": keyring.active, "claims": claims, "mac": mac}


def verify_mac(keyring: Keyring, token: Any) -> dict[str, Any]:
    if not isinstance(token, dict) or set(token) != {"kid", "claims", "mac"} or not isinstance(token["claims"], dict):
        raise ControlError("UNAUTHENTICATED", "malformed credential")
    expected = hmac.new(keyring.get(token["kid"]), canonical(token["claims"]), hashlib.sha256).hexdigest()
    if not isinstance(token["mac"], str) or not hmac.compare_digest(expected, token["mac"]):
        raise ControlError("UNAUTHENTICATED", "signature mismatch")
    return token["claims"]


# ------------------------------------------------------------------ authentication (P0-10)
@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    kind: str                  # "workload" | "operator" | "service"
    scopes: frozenset[str] = field(default_factory=frozenset)


class Authenticator:
    """Verifies workload-identity credentials: MAC, audience, expiry, nonce freshness."""

    def __init__(self, keyring: Keyring, *, clock: Any, audience: str = "gap11",
                 max_skew_s: float = 30.0, nonce_window_s: float = 300.0, telemetry: Telemetry | None = None) -> None:
        self.keyring, self.clock, self.audience = keyring, clock, audience
        self.max_skew_s, self.window = max_skew_s, nonce_window_s
        self.tel = telemetry or Telemetry(clock)
        self._nonces: dict[str, float] = {}
        self._lock = threading.Lock()
        self.available = True

    def issue(self, subject: str, tenant: str, kind: str, scopes: set[str], ttl_s: float = 60.0) -> dict[str, Any]:
        now = self.clock.wall()
        return sign(self.keyring, {"sub": subject, "ten": tenant, "knd": kind, "scp": sorted(scopes),
                                   "aud": self.audience, "iat": now, "exp": now + ttl_s, "nonce": secrets.token_hex(16)})

    def authenticate(self, token: Any) -> Principal:
        if not self.available:
            raise ControlError("DEPENDENCY_UNAVAILABLE", "identity service unavailable")
        try:
            claims = verify_mac(self.keyring, token)
            now = self.clock.wall()
            if claims.get("aud") != self.audience:
                raise ControlError("UNAUTHENTICATED", "wrong audience")
            if not (claims["iat"] - self.max_skew_s <= now < claims["exp"] + self.max_skew_s) or claims["exp"] - claims["iat"] > 3600:
                raise ControlError("UNAUTHENTICATED", "credential expired or not yet valid")
            if claims.get("knd") not in ("workload", "operator", "service"):
                raise ControlError("UNAUTHENTICATED", "bad principal kind")
            with self._lock:
                for n, t in list(self._nonces.items()):
                    if t < now - self.window:
                        del self._nonces[n]
                if claims["nonce"] in self._nonces:
                    raise ControlError("REPLAY_DETECTED")
                if claims["iat"] < now - self.window:
                    raise ControlError("REPLAY_DETECTED", "outside freshness window")
                self._nonces[claims["nonce"]] = now
        except ControlError as exc:
            self.tel.emit("authn", "reject", code=exc.code, severity="WARN")
            raise
        except (KeyError, TypeError) as exc:
            raise ControlError("UNAUTHENTICATED", "malformed claims") from exc
        return Principal(claims["sub"], claims["ten"], claims["knd"], frozenset(claims["scp"]))


# ------------------------------------------------------------------ authorization (P0-11)
SCOPES = {"inventory:read", "inventory:read_sensitive", "lease:allocate", "lease:release", "lease:heartbeat",
          "device:scrub", "device:quarantine", "device:unquarantine", "device:drain", "config:write", "audit:read"}
OPERATOR_ONLY = {"device:scrub", "device:quarantine", "device:unquarantine", "device:drain", "config:write",
                 "inventory:read_sensitive", "audit:read"}


class Policy:
    """Deny-by-default. Decision = explicit allow rule AND scope held AND tenant binding."""

    def __init__(self, rules: list[dict[str, Any]] | None = None, telemetry: Telemetry | None = None) -> None:
        self.rules = rules or []
        self.tel = telemetry
        self.available = True
        for r in self.rules:
            if r["action"] not in SCOPES:
                raise ControlError("CONFIG_INVALID", f"unknown action {r['action']}")

    def decide(self, principal: Principal, action: str, resource: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return self._deny(principal, action, "DEPENDENCY_UNAVAILABLE", "policy engine unavailable")
        if action not in SCOPES:
            return self._deny(principal, action, "POLICY_DENIED", "unknown action")
        if action not in principal.scopes:
            return self._deny(principal, action, "POLICY_DENIED", "scope not held")
        if action in OPERATOR_ONLY and principal.kind != "operator":
            return self._deny(principal, action, "POLICY_DENIED", "operator-only action")
        res_tenant = resource.get("tenant")
        if res_tenant is not None and principal.kind == "workload" and res_tenant != principal.tenant:
            return self._deny(principal, action, "POLICY_DENIED", "cross-tenant resource")
        for r in self.rules:
            if r["action"] == action and r.get("kind", principal.kind) == principal.kind \
               and r.get("tenant", principal.tenant) == principal.tenant \
               and set(r.get("device_kinds", [resource.get("kind")])) >= {resource.get("kind")}:
                return {"allow": True, "rule": r.get("id", "?"), "code": "OK"}
        return self._deny(principal, action, "POLICY_DENIED", "no allow rule")

    def _deny(self, p: Principal, action: str, code: str, why: str) -> dict[str, Any]:
        if self.tel:
            self.tel.emit("authz", "deny", code=code, severity="WARN", detail=f"{action}:{why}")
        return {"allow": False, "code": code, "reason": why}


# ------------------------------------------------------------------ attestation binding (P0-09)
class AttestationVerifier:
    """Verifies that inventory evidence was signed by the node's attestation key and
    binds device stable_id + capability digest + driver/firmware + node identity."""

    def __init__(self, keyring: Keyring, *, clock: Any, max_age_s: float = 3600.0,
                 allowed_firmware: dict[str, set[str]] | None = None) -> None:
        self.keyring, self.clock, self.max_age_s = keyring, clock, max_age_s
        self.allowed_firmware = allowed_firmware or {}

    @staticmethod
    def capability_digest(rec: dict[str, Any]) -> str:
        return hashlib.sha256(canonical({k: rec[k] for k in ("stable_id", "kind", "generation", "memory_gb", "features", "partitions")})).hexdigest()

    def quote(self, rec: dict[str, Any], node_id: str) -> dict[str, Any]:
        """Simulated node attestation agent (stands in for GAP-06)."""
        return sign(self.keyring, {"node": node_id, "stable_id": rec["stable_id"], "cap": self.capability_digest(rec),
                                   "driver": rec["driver"], "firmware": rec["firmware"], "ts": self.clock.wall()})

    def verify(self, rec: dict[str, Any], node_id: str, quote: Any) -> dict[str, Any]:
        try:
            claims = verify_mac(self.keyring, quote)
        except ControlError as exc:
            raise ControlError("ATTESTATION_INVALID", "quote signature invalid") from exc
        problems = []
        if claims.get("node") != node_id:
            problems.append("node")
        if claims.get("stable_id") != rec["stable_id"]:
            problems.append("stable_id")
        if claims.get("cap") != self.capability_digest(rec):
            problems.append("capability")
        if claims.get("driver") != rec["driver"] or claims.get("firmware") != rec["firmware"]:
            problems.append("driver_firmware")
        if self.clock.wall() - claims.get("ts", 0) > self.max_age_s:
            problems.append("stale")
        allowed = self.allowed_firmware.get(rec.get("vendor", ""))
        if allowed is not None and rec["firmware"] not in allowed:
            problems.append("firmware_not_allowed")
        if problems:
            raise ControlError("ATTESTATION_INVALID", ",".join(problems), stable_id=rec["stable_id"])
        return {"attested": True, "stable_id": rec["stable_id"], "cap": claims["cap"]}


# ------------------------------------------------------------------ redaction
_SECRET_PATTERNS = [re.compile(p) for p in (r"(?i)bearer\s+[a-z0-9._\-]+", r"(?i)(secret|password|token|mac|key)\"?\s*[:=]\s*\"?[^\s\",}]+",
                                             r"-----BEGIN [A-Z ]+-----[\s\S]+?-----END [A-Z ]+-----", r"\b[0-9a-f]{64}\b")]
SENSITIVE_KEYS = {"mac", "key", "secret", "password", "token", "credential", "security_tenant", "nonce"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        for p in _SECRET_PATTERNS:
            value = p.sub("[REDACTED]", value)
    return value
