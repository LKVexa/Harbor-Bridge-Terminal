"""PK_BRANCH_CERT/1 signed certification records (MC-08, MC-10, MC-27).

Signature profile: Ed25519 over ``b"PK_BRANCH_CERT/1\\n" + canonical(payload)``
(domain-separated, canonical JSON so bytes are implementation independent).
Private keys never pass through this module's verifier path; issuers use a
``Signer`` (a local key for development, or an adapter to a KMS/HSM).

Verification fails closed on: unknown issuer/key, key purpose mismatch,
revoked key, key used outside its activation window, bad signature, schema or
version error, expiry / not-yet-valid (with bounded skew), missing trusted
time, stale revocation data, revoked/superseded/suspended status, branch
mismatch and artifact digest mismatch.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from . import canonical
from .errors import Inv22Error

CONTRACT = "PK_BRANCH_CERT/1"
DOMAIN = b"PK_BRANCH_CERT/1\n"
ALG = "Ed25519"
_DIG = re.compile(r"^sha256:[0-9a-f]{64}$")
_PAYLOAD_KEYS = {"contract", "cert_id", "component", "artifact_digests", "branch", "baselines",
                 "matrix_digest", "evidence_digest", "issuer", "key_id", "issued_at",
                 "not_before", "not_after", "scope", "waivers"}

try:  # cryptography is an optional-at-import, required-at-use dependency
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    HAVE_CRYPTO = True
except ImportError:  # pragma: no cover - exercised by preflight
    HAVE_CRYPTO = False


def _need_crypto() -> None:
    if not HAVE_CRYPTO:
        raise Inv22Error("INV22.DEPENDENCY.UNAVAILABLE", "cryptography package is required for certification")


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: Any) -> bytes:
    if not isinstance(s, str):
        raise Inv22Error("INV22.CERT.INVALID_SIGNATURE", "signature value must be base64 text")
    try:
        return base64.b64decode(s, validate=True)
    except ValueError:
        raise Inv22Error("INV22.CERT.INVALID_SIGNATURE", "signature value is not valid base64") from None


def signing_bytes(payload: dict) -> bytes:
    return DOMAIN + canonical.dumps(payload)


class Signer(Protocol):
    key_id: str
    issuer: str

    def sign(self, data: bytes) -> bytes: ...


class LocalSigner:
    """Development signer.  Production should adapt a KMS/HSM to the Signer protocol."""

    def __init__(self, key_id: str, issuer: str, private_key=None) -> None:
        _need_crypto()
        self.key_id, self.issuer = key_id, issuer
        self._key = private_key or Ed25519PrivateKey.generate()

    def public_b64(self) -> str:
        return _b64(self._key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))

    def sign(self, data: bytes) -> bytes:
        return self._key.sign(data)

    def __repr__(self) -> str:  # never render key material
        return f"LocalSigner(key_id={self.key_id!r}, issuer={self.issuer!r})"


@dataclass
class TrustedKey:
    key_id: str
    issuer: str
    public_b64: str
    purposes: tuple = ("cert.sign",)
    active_from: int = 0
    retired_at: int | None = None     # no NEW signatures after this; older ones remain valid
    revoked: bool = False             # compromise: every signature by this key is invalid


@dataclass
class TrustStore:
    keys: dict = field(default_factory=dict)
    version: int = 1

    def add(self, key: TrustedKey) -> None:
        if key.key_id in self.keys:
            raise Inv22Error("INV22.VALIDATION.INVALID_INPUT", "duplicate key id", {"key_id": key.key_id})
        self.keys[key.key_id] = key

    def to_dict(self) -> dict:
        return {"schema": "PK_BRANCH_TRUST/1", "version": self.version, "keys": [
            {"key_id": k.key_id, "issuer": k.issuer, "public_key": k.public_b64, "purposes": list(k.purposes),
             "active_from": k.active_from, "retired_at": k.retired_at, "revoked": k.revoked}
            for k in sorted(self.keys.values(), key=lambda k: k.key_id)]}


@dataclass(frozen=True)
class RevocationView:
    """Freshness-bounded revocation snapshot (online fetch or offline cache)."""
    sequence: int
    fetched_at: int
    revoked: frozenset = frozenset()
    superseded: frozenset = frozenset()
    suspended: frozenset = frozenset()


def _require(p: dict) -> None:
    if not isinstance(p, dict):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "certificate payload must be an object")
    canonical.require_supported(p.get("contract", ""), "PK_BRANCH_CERT")
    if set(p) != _PAYLOAD_KEYS:
        diff = sorted(set(p) ^ _PAYLOAD_KEYS)
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "certificate fields mismatch", {"field": diff[0]})
    for k in ("cert_id", "branch", "issuer", "key_id"):
        if not isinstance(p[k], str) or not p[k]:
            raise Inv22Error("INV22.VALIDATION.SCHEMA", f"{k} must be a non-empty string")
    if p["branch"] not in ("standards", "fork"):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "unknown branch")
    comp = p["component"]
    if not isinstance(comp, dict) or set(comp) != {"id", "version"} or not all(isinstance(v, str) and v for v in comp.values()):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "component must be {id, version}")
    ad = p["artifact_digests"]
    if not isinstance(ad, list) or not ad or not all(isinstance(d, str) and _DIG.match(d) for d in ad):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "artifact_digests must be sha256 digests")
    for k in ("matrix_digest", "evidence_digest"):
        if not isinstance(p[k], str) or not _DIG.match(p[k]):
            raise Inv22Error("INV22.VALIDATION.SCHEMA", f"{k} must be a sha256 digest")
    b = p["baselines"]
    if not isinstance(b, dict) or set(b) != {"standards", "fork"} or not all(isinstance(v, str) and _DIG.match(v) for v in b.values()):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "baselines must bind both branch digests")
    ts = [p["issued_at"], p["not_before"], p["not_after"]]
    if not all(isinstance(t, int) and not isinstance(t, bool) and t >= 0 for t in ts):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "timestamps must be non-negative epoch seconds")
    if not p["not_before"] < p["not_after"]:
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "validity window is empty")
    sc = p["scope"]
    if not isinstance(sc, dict) or set(sc) - {"runtimes", "architectures", "environments"}:
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "scope has unknown fields")
    if not isinstance(p["waivers"], list):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "waivers must be a list of waiver ids")


def issue(signer: Signer, *, cert_id: str, component_id: str, component_version: str,
          artifact_digests: list[str], branch: str, baselines: dict, matrix_digest: str,
          evidence_digest: str, issued_at: int, not_after: int, scope: dict | None = None,
          waivers: list | None = None) -> dict:
    payload = {"contract": CONTRACT, "cert_id": cert_id,
               "component": {"id": component_id, "version": component_version},
               "artifact_digests": sorted(artifact_digests), "branch": branch, "baselines": baselines,
               "matrix_digest": matrix_digest, "evidence_digest": evidence_digest,
               "issuer": signer.issuer, "key_id": signer.key_id, "issued_at": issued_at,
               "not_before": issued_at, "not_after": not_after, "scope": scope or {},
               "waivers": sorted(waivers or [])}
    _require(payload)
    sig = signer.sign(signing_bytes(payload))
    return {"payload": payload, "signature": {"alg": ALG, "key_id": signer.key_id, "value": _b64(sig)}}


def verify(envelope: Any, trust: TrustStore, *, now: int | None, branch: str, artifact_digest: str,
           revocation: RevocationView | None, max_revocation_age: int = 3600, skew: int = 120) -> dict:
    """Return the verified payload or raise a structured error.  Never returns on doubt."""
    _need_crypto()
    if now is None:
        raise Inv22Error("INV22.DEPENDENCY.UNAVAILABLE", "trusted time unavailable; refusing to verify")
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "certificate envelope must be {payload, signature}")
    sig = envelope["signature"]
    if not isinstance(sig, dict) or set(sig) != {"alg", "key_id", "value"} or sig["alg"] != ALG:
        raise Inv22Error("INV22.CERT.INVALID_SIGNATURE", "unsupported or malformed signature block")
    p = envelope["payload"]
    _require(p)
    key = trust.keys.get(sig["key_id"])
    if key is None or key.issuer != p["issuer"] or p["key_id"] != sig["key_id"]:
        raise Inv22Error("INV22.CERT.UNKNOWN_ISSUER", "issuer/key not trusted", {"key_id": sig["key_id"]})
    if "cert.sign" not in key.purposes or key.revoked:
        raise Inv22Error("INV22.CERT.INVALID_SIGNATURE", "key not valid for certificate signing", {"key_id": key.key_id})
    if p["issued_at"] < key.active_from or (key.retired_at is not None and p["issued_at"] >= key.retired_at):
        raise Inv22Error("INV22.CERT.INVALID_SIGNATURE", "certificate issued outside key activation window")
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key.public_b64)).verify(_unb64(sig["value"]), signing_bytes(p))
    except (InvalidSignature, ValueError):
        raise Inv22Error("INV22.CERT.INVALID_SIGNATURE", "signature does not verify") from None
    if now + skew < p["not_before"]:
        raise Inv22Error("INV22.CERT.NOT_YET_VALID", "certificate not yet valid", {"cert_id": p["cert_id"]})
    if now - skew >= p["not_after"]:
        raise Inv22Error("INV22.CERT.EXPIRED", "certificate expired", {"cert_id": p["cert_id"]})
    if revocation is None or now - revocation.fetched_at > max_revocation_age:
        raise Inv22Error("INV22.CERT.STALE_REVOCATION", "revocation data missing or stale")
    for bucket, code in ((revocation.revoked, "INV22.CERT.REVOKED"), (revocation.superseded, "INV22.CERT.SUPERSEDED"),
                         (revocation.suspended, "INV22.CERT.SUSPENDED")):
        if p["cert_id"] in bucket:
            raise Inv22Error(code, "certificate is not in a valid state", {"cert_id": p["cert_id"]})
    if p["branch"] != branch:
        raise Inv22Error("INV22.CERT.UNCERTIFIED_BRANCH", "certified for a different branch",
                         {"certified": p["branch"], "requested": branch})
    if artifact_digest not in p["artifact_digests"]:
        raise Inv22Error("INV22.CERT.DIGEST_MISMATCH", "artifact is not the certified artifact")
    return p
