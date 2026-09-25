"""Artifact integrity/provenance verification (item 26).

Images must come from an allowed registry, be pinned by ``@sha256:<64 hex>``
when required, and carry a verifiable signature/attestation when required.
Verification is pluggable (cosign/notation in production); with no verifier
configured and signatures required, admission fails closed.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Protocol

from .lifecycle import PlaneError

_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")


class SignatureVerifier(Protocol):
    def verify(self, image: str) -> bool: ...


class HmacAttestationVerifier:
    """Reference verifier: attestation = HMAC(key, image-digest-ref). Stands in
    for cosign in tests; production swaps in a real verifier."""

    def __init__(self, key: bytes, attestations: dict[str, str]):
        self.key, self.att = key, dict(attestations)

    @staticmethod
    def sign(key: bytes, image: str) -> str:
        return hmac.new(key, image.encode(), hashlib.sha256).hexdigest()

    def verify(self, image: str) -> bool:
        sig = self.att.get(image)
        return sig is not None and hmac.compare_digest(sig, self.sign(self.key, image))


def registry_of(image: str) -> str:
    first = image.split("/", 1)[0]
    if "/" in image and ("." in first or ":" in first or first == "localhost"):
        return first
    return "docker.io"


def verify_image(image: str, *, allowed_registries: list[str], require_digest: bool,
                 require_signature: bool, verifier: SignatureVerifier | None) -> None:
    if not isinstance(image, str) or not image or len(image) > 512 or any(c.isspace() for c in image):
        raise PlaneError("INV67_ARTIFACT_UNVERIFIED", "malformed image reference")
    reg = registry_of(image)
    if not allowed_registries or reg not in allowed_registries:
        raise PlaneError("INV67_ARTIFACT_UNVERIFIED", f"registry {reg} not allowed", image=image)
    if require_digest and not _DIGEST.search(image):
        raise PlaneError("INV67_ARTIFACT_UNVERIFIED", "image not pinned by sha256 digest", image=image)
    if require_signature:
        if verifier is None:
            raise PlaneError("INV67_ARTIFACT_UNVERIFIED", "no signature verifier configured", image=image)
        if not verifier.verify(image):
            raise PlaneError("INV67_ARTIFACT_UNVERIFIED", "signature/attestation did not verify", image=image)
