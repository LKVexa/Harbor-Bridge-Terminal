"""Artifact digest / signature / provenance verification (docs/provenance.md).

An artifact is trusted only when (1) its bytes match the SHA-256 recorded in an
attestation, (2) the attestation is signed by a trusted, unrevoked signer, and
(3) the attestation is bound to the expected artifact type, name and version so
a valid signature cannot be replayed onto a different artifact.
Reference signature scheme: HMAC-SHA256 (``hmac-sha256``).  Asymmetric schemes
(e.g. Sigstore / X.509) plug in through ``SIGNERS``; unknown schemes fail closed.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Any

from .errors import Inv25Error
from .model import canonical_json

ATTESTATION_SCHEMA = "INV25_ARTIFACT_ATTESTATION/1"
ARTIFACT_TYPES = frozenset({"catalogue", "schema", "policy", "package", "pk_core", "fixture", "sbom", "gate"})


class ArtifactVerificationFailed(Inv25Error):
    code = "INV25_ARTIFACT_VERIFICATION_FAILED"


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def attest(data: bytes, *, artifact_type: str, name: str, version: str, signer: str, key: bytes,
           source_revision: str = "", builder: str = "") -> dict[str, Any]:
    att = {"schema": ATTESTATION_SCHEMA, "artifact_type": artifact_type, "name": name, "version": version,
           "digest": sha256(data), "signer": signer, "scheme": "hmac-sha256",
           "source_revision": source_revision, "builder": builder}
    att["signature"] = hmac.new(key, canonical_json(att), hashlib.sha256).hexdigest()
    return att


@dataclass
class TrustPolicy:
    signers: dict[str, bytes]                                 # signer id -> key
    revoked: set[str] = field(default_factory=set)
    approved_versions: dict[tuple[str, str], set[str]] = field(default_factory=dict)  # (type,name)->versions
    require_signature: frozenset[str] = frozenset({"catalogue", "policy", "package", "pk_core", "gate"})

    def verify(self, data: bytes, attestation: dict[str, Any] | None, *, artifact_type: str,
               name: str, version: str) -> dict[str, Any]:
        if artifact_type not in ARTIFACT_TYPES:
            raise ArtifactVerificationFailed("unknown artifact type")
        if not isinstance(attestation, dict) or attestation.get("schema") != ATTESTATION_SCHEMA:
            raise ArtifactVerificationFailed("missing or unknown provenance format")
        # digest first: cheap, and before any parsing of the artifact itself
        if not hmac.compare_digest(str(attestation.get("digest", "")), sha256(data)):
            raise ArtifactVerificationFailed("digest mismatch")
        bound = (attestation.get("artifact_type"), attestation.get("name"), attestation.get("version"))
        if bound != (artifact_type, name, version):
            raise ArtifactVerificationFailed("attestation bound to a different artifact")
        approved = self.approved_versions.get((artifact_type, name))
        if approved is not None and version not in approved:
            raise ArtifactVerificationFailed("version not in approved manifest")
        if artifact_type in self.require_signature or "signature" in attestation:
            if attestation.get("scheme") != "hmac-sha256":
                raise ArtifactVerificationFailed("unsupported signature scheme")
            signer = attestation.get("signer")
            if signer in self.revoked:
                raise ArtifactVerificationFailed("signer revoked")
            key = self.signers.get(signer)
            if key is None:
                raise ArtifactVerificationFailed("untrusted signer")
            body = {k: v for k, v in attestation.items() if k != "signature"}
            expected = hmac.new(key, canonical_json(body), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, str(attestation.get("signature", ""))):
                raise ArtifactVerificationFailed("bad signature")
        return {"verified": True, "digest": attestation["digest"], "signer": attestation.get("signer")}
