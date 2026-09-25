"""MC18 / MC19 / MC20 / MC21 / MC55 — supply-chain trust.

* Ed25519 (RFC 8032) implemented in pure Python for *verification* without third-party
  dependencies; signing is included for fixtures/tests and offline tooling.  It is not
  constant-time, so production signing keys belong in an HSM/KMS (see MC55 docs).
* A :class:`Keyring` with validity windows, revocation and rotation overlap.
* DSSE envelopes and in-toto v1 statements bound to exact subject digests.
* SPDX / CycloneDX SBOM ingestion bound to an image digest.
* Vulnerability admission with explicit scan states (never a boolean).
"""
from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .registry import IntegrityError, ValidationError

# --- Ed25519 -----------------------------------------------------------------------
_p = 2**255 - 19
_q = 2**252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _p - 2, _p) % _p
_SQRT_M1 = pow(2, (_p - 1) // 4, _p)


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _eq(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % _p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % _p == 0


def _recover_x(y, sign):
    if y >= _p:
        return None
    x2 = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p) % _p
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p:
        x = x * _SQRT_M1 % _p
    if (x * x - x2) % _p:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


_gy = 4 * pow(5, _p - 2, _p) % _p
_gx = _recover_x(_gy, 0)
_G = (_gx, _gy, 1, _gx * _gy % _p)


def _compress(P) -> bytes:
    zi = pow(P[2], _p - 2, _p)
    x, y = P[0] * zi % _p, P[1] * zi % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _p)


def _h(m: bytes) -> int:
    return int.from_bytes(hashlib.sha512(m).digest(), "little") % _q


def _expand(secret: bytes):
    if len(secret) != 32:
        raise ValidationError("ed25519 secret must be 32 bytes")
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def ed25519_public_key(secret: bytes) -> bytes:
    return _compress(_mul(_expand(secret)[0], _G))


def ed25519_sign(secret: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(secret)
    A = _compress(_mul(a, _G))
    r = _h(prefix + msg)
    Rs = _compress(_mul(r, _G))
    s = (r + _h(Rs + A + msg) * a) % _q
    return Rs + int.to_bytes(s, 32, "little")


def ed25519_verify(public: bytes, msg: bytes, sig: bytes) -> bool:
    if len(public) != 32 or len(sig) != 64:
        return False
    A = _decompress(public)
    R = _decompress(sig[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= _q:  # reject malleable signatures
        return False
    return _eq(_mul(s, _G), _add(R, _mul(_h(sig[:32] + public + msg), A)))


# --- MC55 keyring with rotation ----------------------------------------------------
class SignatureInvalid(IntegrityError):
    code = "SIGNATURE_INVALID"


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    public: bytes
    not_before: float
    not_after: float
    purposes: frozenset[str] = frozenset({"image", "attestation"})


@dataclass
class Keyring:
    keys: dict[str, TrustedKey] = field(default_factory=dict)
    revoked: dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, key: TrustedKey) -> None:
        if len(key.public) != 32 or key.not_after <= key.not_before:
            raise ValidationError("invalid trusted key")
        with self._lock:
            if key.key_id in self.revoked:
                raise ValidationError("key id was revoked and cannot be re-added")
            self.keys[key.key_id] = key

    def revoke(self, key_id: str, reason: str) -> None:
        with self._lock:
            self.revoked[key_id] = reason
            self.keys.pop(key_id, None)

    def rotate(self, old_id: str, new: TrustedKey, overlap_s: float, now: float) -> None:
        """Add ``new`` and shorten ``old`` to ``now + overlap_s`` so both verify during
        the overlap window; afterwards only ``new`` is valid."""
        self.add(new)
        with self._lock:
            old = self.keys.get(old_id)
            if old is not None:
                self.keys[old_id] = TrustedKey(old.key_id, old.public, old.not_before,
                                               min(old.not_after, now + overlap_s), old.purposes)

    def usable(self, key_id: str, at: float, purpose: str) -> TrustedKey | None:
        with self._lock:
            k = self.keys.get(key_id)
        if k is None or key_id in self.revoked or not (k.not_before <= at < k.not_after) or purpose not in k.purposes:
            return None
        return k

    def expiring(self, now: float, within_s: float) -> list[str]:
        return sorted(k.key_id for k in self.keys.values() if k.not_after - now <= within_s)


def verify_signatures(payload: bytes, sigs: Iterable[tuple[str, bytes]], keyring: Keyring, *,
                      at: float, purpose: str = "image", threshold: int = 1) -> list[str]:
    """Return key ids that validly signed ``payload``; raise unless ``threshold`` distinct keys did."""
    good: list[str] = []
    for key_id, sig in sigs:
        k = keyring.usable(key_id, at, purpose)
        if k and key_id not in good and ed25519_verify(k.public, payload, sig):
            good.append(key_id)
    if len(good) < threshold:
        raise SignatureInvalid(f"{len(good)} valid signature(s); {threshold} required")
    return good


def image_signature_payload(manifest_digest: str, reference: str) -> bytes:
    """Canonical payload binding a signature to a digest *and* the repository it was
    published under (prevents cross-repository replay)."""
    return json.dumps({"critical": {"identity": {"docker-reference": reference},
                                    "image": {"docker-manifest-digest": manifest_digest},
                                    "type": "inv02 container signature"}},
                      sort_keys=True, separators=(",", ":")).encode()


# --- MC19 DSSE / in-toto provenance -------------------------------------------------
INTOTO_STATEMENT_V1 = "https://in-toto.io/Statement/v1"
SLSA_PROVENANCE_V1 = "https://slsa.dev/provenance/v1"
DSSE_INTOTO = "application/vnd.in-toto+json"


def dsse_pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def dsse_sign(payload_type: str, payload: bytes, key_id: str, secret: bytes) -> dict:
    return {"payloadType": payload_type, "payload": base64.b64encode(payload).decode(),
            "signatures": [{"keyid": key_id, "sig": base64.b64encode(ed25519_sign(secret, dsse_pae(payload_type, payload))).decode()}]}


@dataclass(frozen=True)
class VerifiedStatement:
    predicate_type: str
    predicate: dict
    signers: tuple[str, ...]


def verify_attestation(envelope: dict, subject_digest: str, keyring: Keyring, *, at: float,
                       predicate_types: frozenset[str] = frozenset({SLSA_PROVENANCE_V1}),
                       allowed_builders: frozenset[str] | None = None, threshold: int = 1) -> VerifiedStatement:
    if not isinstance(envelope, dict) or envelope.get("payloadType") != DSSE_INTOTO:
        raise SignatureInvalid("not an in-toto DSSE envelope")
    try:
        payload = base64.b64decode(envelope["payload"], validate=True)
        sigs = [(s["keyid"], base64.b64decode(s["sig"], validate=True)) for s in envelope["signatures"]]
    except Exception as exc:
        raise SignatureInvalid("malformed DSSE envelope") from exc
    signers = verify_signatures(dsse_pae(DSSE_INTOTO, payload), sigs, keyring, at=at,
                                purpose="attestation", threshold=threshold)
    try:
        st = json.loads(payload)
    except ValueError as exc:
        raise SignatureInvalid("statement is not JSON") from exc
    if st.get("_type") != INTOTO_STATEMENT_V1:
        raise SignatureInvalid("unsupported statement type")
    algo, hexd = subject_digest.split(":", 1)
    if not any(isinstance(s, dict) and s.get("digest", {}).get(algo) == hexd for s in st.get("subject", [])):
        raise SignatureInvalid("attestation subject does not match artifact digest")
    pt = st.get("predicateType")
    if pt not in predicate_types:
        raise SignatureInvalid(f"predicateType {pt!r} not accepted")
    pred = st.get("predicate") or {}
    if pt == SLSA_PROVENANCE_V1 and allowed_builders is not None:
        builder = ((pred.get("runDetails") or {}).get("builder") or {}).get("id")
        if builder not in allowed_builders:
            raise SignatureInvalid(f"builder {builder!r} not allowed")
    return VerifiedStatement(pt, pred, tuple(signers))


# --- MC20 SBOM ingestion ------------------------------------------------------------
@dataclass(frozen=True)
class SBOM:
    format: str
    subject_digest: str
    components: tuple[tuple[str, str, str | None], ...]  # (name, version, purl)


def ingest_sbom(doc: dict, subject_digest: str) -> SBOM:
    comps: list[tuple[str, str, str | None]] = []
    if doc.get("bomFormat") == "CycloneDX":
        fmt = f"cyclonedx-{doc.get('specVersion')}"
        for c in doc.get("components", []) or []:
            if isinstance(c, dict) and isinstance(c.get("name"), str):
                comps.append((c["name"], str(c.get("version", "")), c.get("purl")))
    elif isinstance(doc.get("spdxVersion"), str):
        fmt = doc["spdxVersion"].lower()
        for pkg in doc.get("packages", []) or []:
            if isinstance(pkg, dict) and isinstance(pkg.get("name"), str):
                purl = next((r.get("referenceLocator") for r in pkg.get("externalRefs", []) or []
                             if isinstance(r, dict) and r.get("referenceType") == "purl"), None)
                comps.append((pkg["name"], str(pkg.get("versionInfo", "")), purl))
    else:
        raise ValidationError("unrecognised SBOM format")
    if len(comps) > 100_000:
        raise ValidationError("SBOM component count exceeds limit")
    return SBOM(fmt, subject_digest, tuple(sorted(set(comps), key=lambda c: (c[0], c[1], c[2] or ""))))


# --- MC21 vulnerability admission ----------------------------------------------------
class ScanState(str, Enum):
    UNSCANNED = "unscanned"
    SCAN_FAILED = "scan-failed"
    SCAN_STALE = "scan-stale"
    CLEAN = "clean"
    VULNERABLE = "vulnerable"
    EXCEPTION_APPROVED = "exception-approved"


_SEV = {"negligible": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(frozen=True)
class ScanResult:
    subject_digest: str
    scanner: str
    db_version: str
    scanned_at: float
    ok: bool
    findings: tuple[tuple[str, str], ...] = ()  # (vuln id, severity)


def scan_state(result: ScanResult | None, *, now: float, max_age_s: float, block_at: str = "high",
               waived: frozenset[str] = frozenset()) -> tuple[ScanState, list[str]]:
    if result is None:
        return ScanState.UNSCANNED, []
    if not result.ok:
        return ScanState.SCAN_FAILED, []
    if now - result.scanned_at > max_age_s:
        return ScanState.SCAN_STALE, []
    blocking = [v for v, sev in result.findings if _SEV.get(sev.lower(), 4) >= _SEV[block_at]]
    if not blocking:
        return ScanState.CLEAN, []
    open_ = [v for v in blocking if v not in waived]
    return (ScanState.EXCEPTION_APPROVED, []) if not open_ else (ScanState.VULNERABLE, open_)


def generate_keypair(seed: bytes | None = None) -> tuple[bytes, bytes]:
    import secrets as _s

    secret = seed or _s.token_bytes(32)
    return secret, ed25519_public_key(secret)
