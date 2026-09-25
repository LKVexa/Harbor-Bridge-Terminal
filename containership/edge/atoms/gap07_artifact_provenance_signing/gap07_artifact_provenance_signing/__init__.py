"""GAP-07 - Artifact provenance/signing.

v6 production modules (asymmetric signatures, KMS/HSM custody, certificate
trust, DSSE/SLSA, transparency, persistence, distribution, policy, registry,
admission, audit export, trusted time) are imported as submodules, e.g.
``from gap07_artifact_provenance_signing.admission import AdmissionController``.
The v5 reference API below is unchanged and remains HMAC/reference-only.
"""
from __future__ import annotations

__version__ = "6.0.0"
ELEMENT_ID = "GAP-07"
ELEMENT_NAME = "Artifact provenance/signing"

from .core import (  # dependency-free public primitives
    ALGORITHM,
    AUDIT_SCHEMA,
    PROVENANCE_SCHEMA,
    SIGNATURE_SCHEMA,
    VERIFICATION_SCHEMA,
    AuditLedger,
    InMemoryKeyProvider,
    KeyProvider,
    ProvenanceInvalid,
    Signature,
    SignatureInvalid,
    SignerUntrusted,
    TrustStore,
    Unsigned,
    VerificationError,
    digest,
    digest_chunks,
    provenance,
    verify_provenance,
)


V6_MODULES = (
    "errors", "canonical", "algorithms", "keys", "trust", "signing", "dsse", "tlog", "store", "distribution",
    "timesrc", "policy", "sbom", "registry", "controls", "telemetry", "audit_export", "admission", "compromise", "service",
)


def build_contract():
    """Lazily load the ``pk_core`` production contract adapter."""
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "ArtifactProvenanceSigningComponent"}:
        from .component import COMPONENT, ArtifactProvenanceSigningComponent
        return {"COMPONENT": COMPONENT, "ArtifactProvenanceSigningComponent": ArtifactProvenanceSigningComponent}[name]
    raise AttributeError(name)


__all__ = [
    "__version__", "V6_MODULES", "ELEMENT_ID", "ELEMENT_NAME", "build_contract",
    "COMPONENT", "ArtifactProvenanceSigningComponent",
    "ALGORITHM", "AUDIT_SCHEMA", "PROVENANCE_SCHEMA", "SIGNATURE_SCHEMA", "VERIFICATION_SCHEMA",
    "AuditLedger", "InMemoryKeyProvider", "KeyProvider", "ProvenanceInvalid", "Signature",
    "SignatureInvalid", "SignerUntrusted", "TrustStore", "Unsigned", "VerificationError",
    "digest", "digest_chunks", "provenance", "verify_provenance",
]
