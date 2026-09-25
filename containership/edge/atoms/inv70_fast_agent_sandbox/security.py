"""Trust controls for INV-70.

C023  boundary authentication of callers (signed, expiring, audience-bound tokens)
C044  node / peer / artifact-provider / control-plane attestation
C045  executable & policy artifact digest, signature, provenance, SBOM, version checks
C048  fail-closed behaviour when the trust store or time source is unavailable
C049  tamper-evident, hash-chained security audit log

Signatures use HMAC-SHA256 through a ``Verifier`` interface keyed by key-id so an
asymmetric (Ed25519 / Sigstore) verifier can be dropped in without changing
callers.  stdlib only.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field

MAX_TOKEN_BYTES = 4096
MAX_CLOCK_SKEW_S = 30
MAX_TOKEN_LIFETIME_S = 900


class AuthError(Exception):
    """Stable, message-safe authentication failure. ``code`` is a PK_FASTBOX reason."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ trust store
class TrustStore:
    """Key-id -> (secret, purpose, not_after). Revocation is immediate.

    ``available`` models the backing KMS/trust-service health (C048); when it is
    False every verification fails closed with ``trust unavailable``.
    """

    def __init__(self):
        self._keys: dict[str, tuple[bytes, str, float]] = {}
        self.revoked: set[str] = set()
        self.available = True
        self._lock = threading.Lock()

    def add(self, kid: str, secret: bytes, purpose: str, not_after: float = float("inf")) -> None:
        if len(secret) < 32:
            raise ValueError("keys must be at least 256 bits")
        with self._lock:
            self._keys[kid] = (secret, purpose, not_after)

    def revoke(self, kid: str) -> None:
        with self._lock:
            self.revoked.add(kid)

    def key(self, kid: str, purpose: str, now: float) -> bytes:
        if not self.available:
            raise AuthError("trust unavailable")
        with self._lock:
            entry = self._keys.get(kid)
            if entry is None or kid in self.revoked:
                raise AuthError("unknown or revoked key")
            secret, kpurpose, not_after = entry
        if kpurpose != purpose:
            raise AuthError("key purpose mismatch")
        if now > not_after:
            raise AuthError("key expired")
        return secret


class Clock:
    """Trusted time source.  ``healthy`` False -> time-dependent checks fail closed (C048)."""

    def __init__(self, fn=time.time):
        self.fn = fn
        self.healthy = True

    def now(self) -> float:
        if not self.healthy:
            raise AuthError("time unavailable")
        return self.fn()


def sign(store_secret: bytes, payload: bytes) -> str:
    return _b64(hmac.new(store_secret, payload, hashlib.sha256).digest())


# ------------------------------------------------------------------ C023 callers
@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    capabilities: frozenset
    token_id: str
    expires: float


def issue_token(store: TrustStore, kid: str, *, subject: str, tenant: str, capabilities,
                audience: str, ttl_s: int, now: float, token_id: str) -> str:
    if not 0 < ttl_s <= MAX_TOKEN_LIFETIME_S:
        raise ValueError("token lifetime out of range")
    claims = {"sub": subject, "ten": tenant, "cap": sorted(capabilities), "aud": audience,
              "iat": int(now), "exp": int(now + ttl_s), "jti": token_id, "kid": kid}
    body = _b64(canonical(claims))
    return body + "." + sign(store.key(kid, "caller", now), body.encode())


class Authenticator:
    """Verifies PK_FASTBOX_RUN caller tokens; replayed token ids are rejected."""

    def __init__(self, store: TrustStore, clock: Clock, audience: str = "inv70"):
        self.store, self.clock, self.audience = store, clock, audience
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def authenticate(self, token: object) -> Principal:
        if type(token) is not str or not token or len(token) > MAX_TOKEN_BYTES or token.count(".") != 1:
            raise AuthError("unauthenticated")
        body, sig = token.split(".")
        try:
            claims = json.loads(_unb64(body))
        except Exception:
            raise AuthError("unauthenticated") from None
        if not isinstance(claims, dict) or type(claims.get("kid")) is not str:
            raise AuthError("unauthenticated")
        now = self.clock.now()
        key = self.store.key(claims["kid"], "caller", now)
        if not hmac.compare_digest(sig, sign(key, body.encode())):
            raise AuthError("unauthenticated")
        if claims.get("aud") != self.audience:
            raise AuthError("wrong audience")
        exp, iat = claims.get("exp"), claims.get("iat")
        if type(exp) is not int or type(iat) is not int or exp - iat > MAX_TOKEN_LIFETIME_S:
            raise AuthError("unauthenticated")
        if now > exp + MAX_CLOCK_SKEW_S or iat > now + MAX_CLOCK_SKEW_S:
            raise AuthError("token expired")
        jti = claims.get("jti")
        if type(jti) is not str or not jti:
            raise AuthError("unauthenticated")
        with self._lock:
            for k in [k for k, e in self._seen.items() if e < now - MAX_CLOCK_SKEW_S]:
                del self._seen[k]
            if jti in self._seen:
                raise AuthError("token replayed")
            self._seen[jti] = exp
        caps = claims.get("cap")
        if not isinstance(caps, list) or not all(type(c) is str for c in caps):
            raise AuthError("unauthenticated")
        ten, sub = claims.get("ten"), claims.get("sub")
        if type(ten) is not str or type(sub) is not str or not ten or not sub:
            raise AuthError("unauthenticated")
        return Principal(sub, ten, frozenset(caps), jti, exp)


# ------------------------------------------------------------------ C044 attestation
REQUIRED_ATTESTATION_ROLES = ("node", "peer", "artifact-provider", "control-plane")


def make_attestation(store: TrustStore, kid: str, *, role: str, identity: str, measurement: str,
                     now: float, ttl_s: int = 3600) -> dict:
    stmt = {"role": role, "id": identity, "measurement": measurement, "iat": int(now), "exp": int(now + ttl_s)}
    return {"statement": stmt, "kid": kid, "sig": sign(store.key(kid, "attest:" + role, now), canonical(stmt))}


def verify_attestation(store: TrustStore, clock: Clock, att: object, *, role: str,
                       expected_measurements: set[str]) -> str:
    if role not in REQUIRED_ATTESTATION_ROLES:
        raise AuthError("unknown attestation role")
    if not isinstance(att, dict) or not isinstance(att.get("statement"), dict):
        raise AuthError("attestation invalid")
    stmt, now = att["statement"], clock.now()
    key = store.key(str(att.get("kid")), "attest:" + role, now)
    if not hmac.compare_digest(str(att.get("sig")), sign(key, canonical(stmt))):
        raise AuthError("attestation invalid")
    if stmt.get("role") != role:
        raise AuthError("attestation role mismatch")
    if not isinstance(stmt.get("exp"), int) or now > stmt["exp"]:
        raise AuthError("attestation expired")
    if stmt.get("measurement") not in expected_measurements:
        raise AuthError("attestation measurement not approved")
    return str(stmt.get("id"))


# ------------------------------------------------------------------ C045 artifacts
@dataclass
class ArtifactPolicy:
    approved_versions: dict = field(default_factory=dict)   # name -> set(version)
    denied_digests: set = field(default_factory=set)
    require_sbom: bool = True
    allowed_builders: set = field(default_factory=lambda: {"inv70-ci"})


def make_manifest(store: TrustStore, kid: str, *, name: str, version: str, content: bytes,
                  builder: str, source_revision: str, sbom: list, now: float) -> dict:
    m = {"name": name, "version": version, "digest": "sha256:" + sha256_hex(content),
         "provenance": {"builder": builder, "source_revision": source_revision, "built": int(now)},
         "sbom": sbom}
    return {"manifest": m, "kid": kid, "sig": sign(store.key(kid, "artifact", now), canonical(m))}


def verify_artifact(store: TrustStore, clock: Clock, policy: ArtifactPolicy, signed: object,
                    content: bytes) -> dict:
    """Return the verified manifest or raise AuthError. Order: sig, digest, deny, version, provenance, SBOM."""
    if not isinstance(signed, dict) or not isinstance(signed.get("manifest"), dict):
        raise AuthError("artifact unsigned")
    m, now = signed["manifest"], clock.now()
    key = store.key(str(signed.get("kid")), "artifact", now)
    if not hmac.compare_digest(str(signed.get("sig")), sign(key, canonical(m))):
        raise AuthError("artifact signature invalid")
    digest = "sha256:" + sha256_hex(content)
    if m.get("digest") != digest:
        raise AuthError("artifact digest mismatch")
    if digest in policy.denied_digests:
        raise AuthError("artifact denied")
    if m.get("version") not in policy.approved_versions.get(m.get("name"), set()):
        raise AuthError("artifact version not approved")
    prov = m.get("provenance") or {}
    if prov.get("builder") not in policy.allowed_builders or not prov.get("source_revision"):
        raise AuthError("artifact provenance invalid")
    if policy.require_sbom and not (isinstance(m.get("sbom"), list) and m["sbom"]):
        raise AuthError("artifact sbom missing")
    return m


# ------------------------------------------------------------------ C049 audit log
class AuditLog:
    """Append-only hash-chained, HMAC-sealed audit log.  ``verify`` detects edit,
    reorder, deletion and truncation (via the sealed head)."""

    GENESIS = "0" * 64

    def __init__(self, seal_key: bytes, sink=None):
        if len(seal_key) < 32:
            raise ValueError("seal key must be at least 256 bits")
        self._key = seal_key
        self.entries: list[dict] = []
        self.head = self.GENESIS
        self.sink = sink
        self.write_failures = 0
        self._lock = threading.Lock()

    def append(self, event: str, **fields) -> dict:
        with self._lock:
            body = {"seq": len(self.entries), "ts": round(time.time(), 6), "event": event,
                    "prev": self.head, **fields}
            h = sha256_hex(canonical(body))
            entry = {**body, "hash": h, "mac": sign(self._key, h.encode())}
            if self.sink is not None:
                try:
                    self.sink.write(json.dumps(entry, sort_keys=True) + "\n")
                    self.sink.flush()
                except Exception:
                    self.write_failures += 1
                    raise AuthError("audit unavailable")
            self.entries.append(entry)
            self.head = h
            return entry

    def sealed_head(self) -> dict:
        return {"count": len(self.entries), "head": self.head, "mac": sign(self._key, f"{len(self.entries)}:{self.head}".encode())}

    @classmethod
    def verify(cls, entries: list[dict], seal_key: bytes, sealed_head: dict | None = None) -> tuple[bool, str]:
        prev = cls.GENESIS
        for i, e in enumerate(entries):
            body = {k: v for k, v in e.items() if k not in ("hash", "mac")}
            if body.get("seq") != i or body.get("prev") != prev:
                return False, f"chain break at {i}"
            h = sha256_hex(canonical(body))
            if h != e.get("hash") or not hmac.compare_digest(e.get("mac", ""), sign(seal_key, h.encode())):
                return False, f"tamper at {i}"
            prev = h
        if sealed_head is not None:
            exp = sign(seal_key, f"{sealed_head.get('count')}:{sealed_head.get('head')}".encode())
            if not hmac.compare_digest(str(sealed_head.get("mac")), exp):
                return False, "sealed head invalid"
            if sealed_head.get("count") != len(entries) or sealed_head.get("head") != prev:
                return False, "truncation detected"
        return True, "ok"
