"""Trust roots for PLN-04: signed envelopes, actor authn/authz, signed
classification, artifact verification, attestation evidence and secrets.

Covers M05, M06, M07, M08, M09, M18, M37 at the *verification-contract* level.

Honest boundary
---------------
The standard library offers HMAC but no asymmetric signatures.  Every
verifier here is written against the :class:`Verifier` protocol and ships an
``HmacVerifier`` so the contract, freshness, replay and allowlist logic is
real and tested.  Production must register an asymmetric verifier (Ed25519 /
ECDSA / Sigstore / TPM-quote / SEV-SNP / TDX report verifier) -- that is an
external dependency recorded as PARTIAL in ``docs/TRACEABILITY.md``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Protocol

from .errors import PlaneError

ENVELOPE_VERSION = "PK_SIGNED/1"
_B64 = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    if not _B64.match(text or ""):
        raise ValueError("invalid base64url")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- signing

class Verifier(Protocol):
    algorithm: str

    def verify(self, kid: str, message: bytes, signature: bytes) -> bool: ...


class Signer(Protocol):
    algorithm: str
    kid: str

    def sign(self, message: bytes) -> bytes: ...


@dataclass
class HmacKeyring:
    """Keyring for the stdlib reference algorithm ``HS256``.

    Keys are referenced by ``kid`` so rotation is overlap-based: add the new
    key, move signers, then retire the old kid.  Retired kids are refused.
    """

    keys: dict[str, bytes] = field(default_factory=dict)
    retired: set[str] = field(default_factory=set)
    algorithm: str = "HS256"

    def add(self, kid: str, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("HMAC keys must be at least 32 bytes")
        if kid in self.keys or kid in self.retired:
            raise ValueError(f"kid already used: {kid!r}")
        self.keys[kid] = bytes(key)

    def retire(self, kid: str) -> None:
        self.keys.pop(kid, None)
        self.retired.add(kid)

    def verify(self, kid: str, message: bytes, signature: bytes) -> bool:
        key = self.keys.get(kid)
        if key is None or kid in self.retired:
            return False
        return hmac.compare_digest(hmac.new(key, message, hashlib.sha256).digest(), signature)

    def signer(self, kid: str) -> "HmacSigner":
        if kid not in self.keys:
            raise KeyError(kid)
        return HmacSigner(kid=kid, key=self.keys[kid])


@dataclass(frozen=True)
class HmacSigner:
    kid: str
    key: bytes
    algorithm: str = "HS256"

    def sign(self, message: bytes) -> bytes:
        return hmac.new(self.key, message, hashlib.sha256).digest()


def seal(signer: Signer, purpose: str, claims: Mapping[str, object]) -> str:
    """Produce ``b64(header).b64(claims).b64(sig)`` bound to a purpose."""
    header = {"v": ENVELOPE_VERSION, "alg": signer.algorithm, "kid": signer.kid, "purpose": purpose}
    head = _b64e(canonical(header))
    body = _b64e(canonical(dict(claims)))
    sig = _b64e(signer.sign(f"{head}.{body}".encode("ascii")))
    return f"{head}.{body}.{sig}"


def open_sealed(token: str, purpose: str, verifiers: Mapping[str, Verifier]) -> tuple[dict, dict]:
    """Verify an envelope and return ``(header, claims)`` or raise ValueError."""
    if not isinstance(token, str) or len(token) > 8192 or token.count(".") != 2:
        raise ValueError("malformed envelope")
    head_b, body_b, sig_b = token.split(".")
    header = json.loads(_b64d(head_b))
    if not isinstance(header, dict) or header.get("v") != ENVELOPE_VERSION:
        raise ValueError("unsupported envelope version")
    if header.get("purpose") != purpose:
        raise ValueError("envelope purpose mismatch")  # prevents cross-protocol replay
    verifier = verifiers.get(header.get("alg"))
    if verifier is None:
        raise ValueError("algorithm not accepted")
    if not verifier.verify(str(header.get("kid")), f"{head_b}.{body_b}".encode("ascii"), _b64d(sig_b)):
        raise ValueError("signature invalid")
    claims = json.loads(_b64d(body_b))
    if not isinstance(claims, dict):
        raise ValueError("claims must be an object")
    return header, claims


# --------------------------------------------------------------------------- trusted time / replay (M37)

class TrustedClock:
    """Wall clock with an explicit skew budget; refuses to run backwards."""

    def __init__(self, source: Callable[[], float] = time.time, max_skew_s: float = 30.0) -> None:
        self._source = source
        self.max_skew_s = max_skew_s
        self._last = 0.0
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            value = float(self._source())
            if value + self.max_skew_s < self._last:
                raise PlaneError("PLN04-ATT-002", details={"reason": "trusted clock regressed beyond skew budget"})
            self._last = max(self._last, value)
            return value


class ReplayCache:
    """Bounded nonce cache; a nonce is accepted once until its expiry."""

    def __init__(self, capacity: int = 65536) -> None:
        self._seen: "OrderedDict[str, float]" = OrderedDict()
        self._capacity = capacity
        self._lock = threading.Lock()

    def check_and_add(self, nonce: str, expires_at: float, now: float) -> bool:
        with self._lock:
            for key in [k for k, exp in self._seen.items() if exp < now][:1024]:
                del self._seen[key]
            if nonce in self._seen:
                return False
            if len(self._seen) >= self._capacity:
                # fail closed: a full cache cannot prove non-replay
                return False
            self._seen[nonce] = expires_at
            return True


def _check_times(claims: Mapping[str, object], clock: TrustedClock, max_age_s: float) -> float:
    now = clock.now()
    iat, exp = claims.get("iat"), claims.get("exp")
    if not isinstance(iat, (int, float)) or not isinstance(exp, (int, float)) or isinstance(iat, bool) or isinstance(exp, bool):
        raise ValueError("iat/exp required")
    if iat > now + clock.max_skew_s:
        raise ValueError("issued in the future")
    if exp < now - clock.max_skew_s:
        raise ValueError("expired")
    if exp - iat > max_age_s or now - iat > max_age_s + clock.max_skew_s:
        raise ValueError("lifetime exceeds policy")
    return now


# --------------------------------------------------------------------------- actors (M08)

CAPABILITIES = frozenset({
    "admission:create", "admission:teardown", "admission:teardown:privileged",
    "catalogue:read", "catalogue:attest", "plane:operate", "plane:read",
})


@dataclass(frozen=True)
class Actor:
    subject: str
    tenant: str | None
    capabilities: frozenset[str]
    token_id: str


class Authenticator:
    def __init__(self, verifiers: Mapping[str, Verifier], clock: TrustedClock, *, audience: str,
                 max_token_age_s: float = 900.0, replay: ReplayCache | None = None) -> None:
        self._verifiers = dict(verifiers)
        self._clock = clock
        self._audience = audience
        self._max_age = max_token_age_s
        self._replay = replay

    def authenticate(self, token: str | None) -> Actor:
        if not token:
            raise PlaneError("PLN04-AUTHN-001", details={"reason": "missing credential"})
        try:
            _, claims = open_sealed(token, "pln04.actor", self._verifiers)
            now = _check_times(claims, self._clock, self._max_age)
            if claims.get("aud") != self._audience:
                raise ValueError("audience mismatch")
            caps = claims.get("caps")
            if not isinstance(caps, list) or not set(caps) <= CAPABILITIES:
                raise ValueError("unknown capability")
            sub, jti = claims.get("sub"), claims.get("jti")
            if not isinstance(sub, str) or not sub or not isinstance(jti, str) or not jti:
                raise ValueError("sub/jti required")
            tenant = claims.get("tenant")
            if tenant is not None and not isinstance(tenant, str):
                raise ValueError("tenant must be string")
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise PlaneError("PLN04-AUTHN-001", details={"reason": str(exc)}) from None
        if self._replay is not None and claims.get("one_shot") and not self._replay.check_and_add(jti, float(claims["exp"]), now):
            raise PlaneError("PLN04-AUTHN-001", details={"reason": "token replayed"})
        return Actor(subject=sub, tenant=tenant, capabilities=frozenset(caps), token_id=jti)


def authorize(actor: Actor, capability: str, *, tenant: str | None = None) -> None:
    """Capability check; tenant-scoped actors may only act on their own tenant."""
    if capability not in CAPABILITIES:
        raise ValueError(f"unknown capability {capability!r}")
    if capability not in actor.capabilities:
        raise PlaneError("PLN04-AUTHZ-001", details={"reason": capability})
    if tenant is not None and actor.tenant is not None and actor.tenant != tenant:
        raise PlaneError("PLN04-AUTHZ-001", details={"reason": "actor bound to another tenant", "tenant": tenant})


def issue_actor_token(signer: Signer, *, subject: str, tenant: str | None, caps: Iterable[str],
                      audience: str, ttl_s: float = 300.0, now: float | None = None, one_shot: bool = False) -> str:
    now = time.time() if now is None else now
    return seal(signer, "pln04.actor", {
        "sub": subject, "tenant": tenant, "caps": sorted(caps), "aud": audience,
        "iat": now, "exp": now + ttl_s, "jti": _b64e(os.urandom(12)), "one_shot": one_shot,
    })


# --------------------------------------------------------------------------- classification (M07)

@dataclass(frozen=True)
class Classification:
    workload: str
    tenant: str
    trust_class: str
    policy_digest: str
    issuer: str


class ClassificationVerifier:
    def __init__(self, verifiers: Mapping[str, Verifier], clock: TrustedClock, *,
                 trusted_issuers: Iterable[str], max_age_s: float = 3600.0) -> None:
        self._verifiers = dict(verifiers)
        self._clock = clock
        self._issuers = frozenset(trusted_issuers)
        self._max_age = max_age_s

    def verify(self, token: str | None, *, workload: str, tenant: str) -> Classification:
        from .runtime import TRUST_CLASSES
        try:
            if not token:
                raise ValueError("classification token required")
            _, c = open_sealed(token, "pln04.classification", self._verifiers)
            _check_times(c, self._clock, self._max_age)
            if c.get("iss") not in self._issuers:
                raise ValueError("untrusted issuer")
            if c.get("workload") != workload or c.get("tenant") != tenant:
                raise ValueError("classification bound to a different workload/tenant")
            if c.get("trust_class") not in TRUST_CLASSES:
                raise ValueError("unknown trust class")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(c.get("policy_digest"))):
                raise ValueError("policy digest required")
        except (ValueError, json.JSONDecodeError) as exc:
            raise PlaneError("PLN04-POL-002", details={"reason": str(exc)}) from None
        return Classification(workload, tenant, c["trust_class"], c["policy_digest"], c["iss"])


def issue_classification(signer: Signer, *, issuer: str, workload: str, tenant: str, trust_class: str,
                         policy_digest: str, ttl_s: float = 600.0, now: float | None = None) -> str:
    now = time.time() if now is None else now
    return seal(signer, "pln04.classification", {
        "iss": issuer, "workload": workload, "tenant": tenant, "trust_class": trust_class,
        "policy_digest": policy_digest, "iat": now, "exp": now + ttl_s,
    })


# --------------------------------------------------------------------------- artifacts (M09)

class ArtifactPolicy:
    """Digest allowlist + signed provenance statement per artifact digest."""

    def __init__(self, verifiers: Mapping[str, Verifier], *, trusted_builders: Iterable[str]) -> None:
        self._verifiers = dict(verifiers)
        self._builders = frozenset(trusted_builders)
        self._allow: dict[str, dict] = {}
        self._revoked: set[str] = set()
        self._lock = threading.Lock()

    def register(self, provenance_token: str) -> str:
        """Verify a signed provenance statement and allowlist its digest."""
        try:
            _, stmt = open_sealed(provenance_token, "pln04.provenance", self._verifiers)
            digest = stmt.get("digest")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(digest)):
                raise ValueError("digest required")
            if stmt.get("builder") not in self._builders:
                raise ValueError("untrusted builder")
            tiers = stmt.get("tiers")
            if not isinstance(tiers, list) or not tiers:
                raise ValueError("tiers required")
        except (ValueError, json.JSONDecodeError) as exc:
            raise PlaneError("PLN04-POL-003", details={"reason": str(exc)}) from None
        with self._lock:
            if digest in self._revoked:
                raise PlaneError("PLN04-POL-003", details={"reason": "digest revoked"})
            self._allow[digest] = stmt
        return digest

    def revoke(self, digest: str) -> None:
        with self._lock:
            self._revoked.add(digest)
            self._allow.pop(digest, None)

    def check(self, digest: str | None, tier: str, content: bytes | None = None) -> None:
        with self._lock:
            stmt = self._allow.get(digest or "")
            revoked = digest in self._revoked
        if revoked or stmt is None:
            raise PlaneError("PLN04-POL-003", details={"reason": "digest not allowlisted", "tier": tier})
        if tier not in stmt["tiers"]:
            raise PlaneError("PLN04-POL-003", details={"reason": "artifact not approved for tier", "tier": tier})
        if content is not None and sha256_digest(content) != digest:
            raise PlaneError("PLN04-POL-003", details={"reason": "content does not match digest"})


def issue_provenance(signer: Signer, *, digest: str, builder: str, source: str, tiers: Iterable[str]) -> str:
    return seal(signer, "pln04.provenance", {"digest": digest, "builder": builder, "source": source, "tiers": sorted(tiers)})


# --------------------------------------------------------------------------- attestation (M05, M06, M37)

@dataclass(frozen=True)
class CapabilityReport:
    """M05 - normalised hardware/hypervisor capability discovery result."""

    node_id: str
    arch: str
    features: frozenset[str]
    hypervisor: str | None

    def supports(self, tier: str) -> bool:
        need = TIER_HARDWARE_REQUIREMENTS[tier]
        return need <= self.features


#: Minimum discovered features before a tier may even be *offered* for attestation.
TIER_HARDWARE_REQUIREMENTS: Mapping[str, frozenset[str]] = {
    "process": frozenset(),
    "wasm": frozenset(),
    "unikernel": frozenset({"virtualization"}),
    "microvm": frozenset({"virtualization", "iommu"}),
    "vm": frozenset({"virtualization", "iommu", "memory_encryption"}),
}


def discover_local_capabilities(node_id: str, cpuinfo_path: str = "/proc/cpuinfo") -> CapabilityReport:
    """Best-effort Linux discovery (GAP-02 adapter).  Missing evidence => feature absent."""
    import platform
    features: set[str] = set()
    try:
        with open(cpuinfo_path, encoding="utf-8", errors="replace") as fh:
            flags = set(fh.read(1 << 20).split())
        if flags & {"vmx", "svm"}:
            features.add("virtualization")
        if flags & {"sev", "sev_es", "sme", "tdx_guest"}:
            features.add("memory_encryption")
    except OSError:
        pass
    if os.path.isdir("/sys/kernel/iommu_groups") and os.listdir("/sys/kernel/iommu_groups"):
        features.add("iommu")
    if os.path.exists("/dev/kvm"):
        features.add("kvm")
    return CapabilityReport(node_id, platform.machine() or "unknown", frozenset(features), "kvm" if "kvm" in features else None)


class AttestationVerifier:
    """M06/M37 - verify signed tier-attestation evidence with nonce, freshness and replay rules.

    ``evidence`` claims: node_id, tier, nonce, measurement, iat, exp.  The
    nonce must have been issued by :meth:`challenge` for this node and is
    single-use.  The measurement must be in the reference-value set.
    """

    def __init__(self, verifiers: Mapping[str, Verifier], clock: TrustedClock, *,
                 reference_measurements: Mapping[str, Iterable[str]], max_age_s: float = 300.0) -> None:
        self._verifiers = dict(verifiers)
        self._clock = clock
        self._refs = {tier: frozenset(v) for tier, v in reference_measurements.items()}
        self._max_age = max_age_s
        self._outstanding: dict[str, tuple[str, float]] = {}
        self._replay = ReplayCache()
        self._lock = threading.Lock()

    @property
    def max_age_s(self) -> float:
        return self._max_age

    def challenge(self, node_id: str) -> str:
        nonce = _b64e(os.urandom(24))
        with self._lock:
            now = self._clock.now()
            self._outstanding = {k: v for k, v in self._outstanding.items() if v[1] >= now}
            if len(self._outstanding) > 4096:
                raise PlaneError("PLN04-CAP-002", details={"reason": "too many outstanding challenges"})
            self._outstanding[nonce] = (node_id, now + self._max_age)
        return nonce

    def verify(self, evidence: str, *, node_id: str, tier: str) -> float:
        """Return the evidence expiry timestamp or raise PLN04-ATT-002."""
        try:
            _, c = open_sealed(evidence, "pln04.attestation", self._verifiers)
            now = _check_times(c, self._clock, self._max_age)
            if c.get("node_id") != node_id or c.get("tier") != tier:
                raise ValueError("evidence bound to another node/tier")
            nonce = c.get("nonce")
            with self._lock:
                issued = self._outstanding.pop(nonce, None)
            if issued is None or issued[0] != node_id:
                raise ValueError("unknown or foreign nonce")
            if not self._replay.check_and_add(nonce, float(c["exp"]), now):
                raise ValueError("nonce replayed")
            if c.get("measurement") not in self._refs.get(tier, ()):
                raise ValueError("measurement not in reference values")
        except (ValueError, json.JSONDecodeError) as exc:
            raise PlaneError("PLN04-ATT-002", details={"reason": str(exc), "tier": tier}) from None
        return float(c["exp"])


def issue_attestation(signer: Signer, *, node_id: str, tier: str, nonce: str, measurement: str,
                      ttl_s: float = 120.0, now: float | None = None) -> str:
    now = time.time() if now is None else now
    return seal(signer, "pln04.attestation", {"node_id": node_id, "tier": tier, "nonce": nonce,
                                              "measurement": measurement, "iat": now, "exp": now + ttl_s})


# --------------------------------------------------------------------------- secrets (M18)

class SecretProvider(Protocol):
    def get(self, name: str) -> bytes: ...


class EnvSecretProvider:
    """Reads ``PLN04_SECRET_<NAME>`` as base64url.  For dev/test and as KMS shim."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._env = os.environ if environ is None else environ

    def get(self, name: str) -> bytes:
        if not re.fullmatch(r"[A-Z0-9_]{1,64}", name):
            raise ValueError("invalid secret name")
        raw = self._env.get(f"PLN04_SECRET_{name}")
        if raw is None:
            raise PlaneError("PLN04-DEP-001", details={"dependency": "secrets", "reason": f"secret {name} unavailable"})
        return _b64d(raw)


class FileSecretProvider:
    """Reads mounted secret files (e.g. Kubernetes/Vault agent tmpfs); refuses group/world-readable files on POSIX."""

    def __init__(self, directory: str) -> None:
        self._dir = directory

    def get(self, name: str) -> bytes:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name) or name.startswith("."):
            raise ValueError("invalid secret name")
        path = os.path.join(self._dir, name)
        try:
            st = os.stat(path)
            if os.name == "posix" and st.st_mode & 0o077:
                raise PlaneError("PLN04-DEP-001", details={"dependency": "secrets", "reason": "secret file permissions too open"})
            with open(path, "rb") as fh:
                return fh.read(65536).strip()
        except OSError:
            raise PlaneError("PLN04-DEP-001", details={"dependency": "secrets", "reason": f"secret {name} unavailable"}) from None


_REDACT = re.compile(r"(?i)(token|secret|password|passwd|authorization|api[_-]?key|private[_-]?key|credential|evidence|signature)")
_REDACT_VALUE = re.compile(r"(?:\b(?:sk|pk|rk)[-_](?:live|test)[-_][A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,})")


def redact(value: object, _depth: int = 0) -> object:
    """Recursively redact secret-looking keys and token-shaped values (bounded depth)."""
    if _depth > 8:
        return "[TRUNCATED]"
    if isinstance(value, Mapping):
        return {str(k): ("[REDACTED]" if _REDACT.search(str(k)) else redact(v, _depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth + 1) for v in value[:256]]
    if isinstance(value, str):
        return _REDACT_VALUE.sub("[REDACTED]", value[:4096])
    return value
