"""Artifact signature, digest and provenance verification (MC-029 / MC-030).

Admission no longer trusts a ``signer`` string.  Every component must:

1. reference its image by immutable digest ``registry/repo@sha256:<64 hex>``
   (tags are rejected: ``IMAGE_NOT_PINNED``);
2. come from an approved registry (exact host match, case-insensitive);
3. carry an Ed25519 ``signature`` (base64url) by an approved signer key over
   the domain-separated payload ``PK_ECP_SIG/1\\0 || canonical({image, digest})``;
4. present every attestation type required by policy (SLSA provenance /
   SBOM), each bound to a sha256 digest.

The signer key set is configuration (public keys only; INV-66 never holds
signing keys).  Ed25519 uses the ``cryptography`` package; if it is not
installed verification fails closed.  Transparency-log inclusion checking is
an adapter hook (:class:`TransparencyLog`) wired by GAP-07.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Iterable, Protocol

from .canonical import canonical_json
from .errors import Error

SIG_DOMAIN = b"PK_ECP_SIG/1\0"
IMAGE_RE = re.compile(r"^(?P<registry>[a-z0-9][a-z0-9.-]*(?::[0-9]{1,5})?)/(?P<repo>[a-z0-9._/-]{1,512})@sha256:(?P<digest>[0-9a-f]{64})$")


def ed25519_verify(public_key: bytes, data: bytes, sig: bytes) -> bool:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:  # fail closed
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(sig, data)
        return True
    except (InvalidSignature, ValueError):
        return False


def signing_payload(image: str) -> bytes:
    m = IMAGE_RE.match(image)
    d = m.group("digest") if m else ""
    return SIG_DOMAIN + canonical_json({"image": image, "digest": f"sha256:{d}"})


def sign_image(private_key: bytes, image: str) -> str:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sig = Ed25519PrivateKey.from_private_bytes(private_key).sign(signing_payload(image))
    return base64.urlsafe_b64encode(sig).rstrip(b"=").decode()


@dataclass(frozen=True)
class SignerKey:
    id: str
    public_key: bytes
    not_after: int | None = None


class TransparencyLog(Protocol):
    def included(self, image: str, signature: str) -> bool: ...


@dataclass
class ProvenanceVerifier:
    registries: frozenset[str]
    signers: dict[str, SignerKey]
    required_attestations: frozenset[str] = frozenset()
    transparency: TransparencyLog | None = None

    def verify_component(self, comp: dict, label: str, now: int) -> list[Error]:
        errs: list[Error] = []
        image = comp.get("image")
        m = IMAGE_RE.match(image) if isinstance(image, str) else None
        if m is None:
            code = "IMAGE_NOT_PINNED" if isinstance(image, str) and "/" in image and "@sha256:" not in image else "IMAGE_MALFORMED"
            errs.append(Error(code, "image must be registry/repo@sha256:<digest>", label))
        else:
            reg = m.group("registry").lower()
            if reg not in self.registries:
                errs.append(Error("REGISTRY_NOT_APPROVED", f"registry {reg} not approved", label, {"registry": reg}))
        signer_id = comp.get("signer")
        key = self.signers.get(signer_id) if isinstance(signer_id, str) else None
        if key is None or (key.not_after is not None and now > key.not_after):
            errs.append(Error("SIGNER_NOT_APPROVED", f"signer {signer_id!r} not approved or expired", label))
        elif m is not None:
            sig_txt = comp.get("signature")
            try:
                sig = base64.urlsafe_b64decode(sig_txt + "=" * (-len(sig_txt) % 4)) if isinstance(sig_txt, str) else b""
            except Exception:
                sig = b""
            if not ed25519_verify(key.public_key, signing_payload(image), sig):
                errs.append(Error("SIGNATURE_INVALID", "signature does not verify", label))
            elif self.transparency is not None and not self.transparency.included(image, sig_txt):
                errs.append(Error("SIGNATURE_INVALID", "signature not present in transparency log", label))
        present = {a.get("type") for a in comp.get("attestations", []) if isinstance(a, dict)}
        for missing in sorted(self.required_attestations - present):
            errs.append(Error("ATTESTATION_MISSING", f"missing {missing}", label, {"type": missing}))
        return errs


def signer_keys(entries: Iterable[dict]) -> dict[str, SignerKey]:
    out = {}
    for e in entries:
        pk = bytes.fromhex(e["public_key"])
        if len(pk) != 32:
            raise ValueError(f"signer {e['id']}: ed25519 public key must be 32 bytes")
        out[e["id"]] = SignerKey(e["id"], pk, e.get("not_after"))
    return out
