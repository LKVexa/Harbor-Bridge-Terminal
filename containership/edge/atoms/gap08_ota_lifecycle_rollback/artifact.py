"""Artifact digest/content verifier integration (component 6; GAP-07 contract).

GAP-07 signs a ``PK_VERIFICATION/1`` statement whose *subject* is both the
logical bundle id and the exact SHA-256 content digest.  GAP-08:

* verifies the statement signature against GAP-07's verifier keys;
* rejects wrong-subject, expired, not-yet-valid, revoked, unsigned and
  algorithm-downgraded statements;
* re-hashes the actual bytes (streamed, bounded memory) before distribution
  and on the node before install, refusing any mismatch;
* persists only the verification *digest reference*, never the statement's
  key material.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Mapping

from .common import Clock, KeyRing, SystemClock, digest_of, verify_envelope
from .errors import ArtifactMismatch, EvidenceRejected

VERIFICATION_SCHEMA = "PK_VERIFICATION/1"
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
ALLOWED_ALGORITHMS = frozenset({"ed25519", "ecdsa-p256-sha256", "rsa-pss-sha256", "hmac-sha256-test"})


@dataclass(frozen=True)
class VerifiedArtifact:
    bundle: str
    digest: str               # sha256:<hex>
    size: int | None
    verification_ref: str     # digest of the signed statement
    verifier: str
    expires_at: float

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ArtifactVerifier:
    keyring: KeyRing
    verifier_keys: set[str]
    clock: Clock = field(default_factory=SystemClock)
    revoked_digests: set[str] = field(default_factory=set)
    allowed_algorithms: frozenset[str] = ALLOWED_ALGORITHMS

    def admit(self, envelope: Mapping[str, Any], *, bundle: str) -> VerifiedArtifact:
        if envelope.get("key_id") not in self.verifier_keys:
            raise EvidenceRejected("verification not signed by a GAP-07 verifier key", resource=bundle)
        body = verify_envelope(self.keyring, envelope)
        if body is None:
            raise EvidenceRejected("verification signature invalid or key revoked", resource=bundle)
        if body.get("schema") != VERIFICATION_SCHEMA or body.get("kind") != "bundle":
            raise EvidenceRejected("unsupported verification schema/kind", resource=bundle)
        if body.get("verified") is not True:
            raise EvidenceRejected("verifier did not verify the artifact", resource=bundle)
        if body.get("subject") != bundle:
            raise EvidenceRejected(f"verification subject {body.get('subject')!r} != {bundle!r}", resource=bundle)
        digest = body.get("digest")
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise EvidenceRejected("verification lacks a sha256:<hex> content digest", resource=bundle)
        if digest in self.revoked_digests:
            raise EvidenceRejected("artifact digest has been revoked", resource=bundle)
        if body.get("algorithm") not in self.allowed_algorithms:
            raise EvidenceRejected(f"signature algorithm {body.get('algorithm')!r} not allowed (downgrade?)",
                                   resource=bundle)
        now = self.clock.now()
        nb, exp = body.get("verified_at"), body.get("expires_at")
        if not isinstance(nb, (int, float)) or not isinstance(exp, (int, float)) or nb > now + 5 or exp <= now:
            raise EvidenceRejected("verification is expired or not yet valid", resource=bundle)
        size = body.get("size")
        return VerifiedArtifact(bundle, digest, size if isinstance(size, int) else None, digest_of(dict(envelope)),
                                str(body.get("verifier")), float(exp))

    def still_valid(self, artifact: VerifiedArtifact) -> bool:
        """Re-check before deferred retries: expiry and revocation may have changed."""
        return artifact.expires_at > self.clock.now() and artifact.digest not in self.revoked_digests


def hash_stream(stream: BinaryIO, *, chunk: int = 1 << 20, max_bytes: int | None = None) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    while True:
        block = stream.read(chunk)
        if not block:
            break
        n += len(block)
        if max_bytes is not None and n > max_bytes:
            raise ArtifactMismatch("artifact exceeds declared size")
        h.update(block)
    return "sha256:" + h.hexdigest(), n


def verify_content(artifact: VerifiedArtifact, path: str | Path) -> None:
    with open(path, "rb") as fh:
        digest, size = hash_stream(fh, max_bytes=artifact.size)
    if digest != artifact.digest or (artifact.size is not None and size != artifact.size):
        raise ArtifactMismatch(f"content digest {digest} != verified {artifact.digest}", resource=artifact.bundle)
