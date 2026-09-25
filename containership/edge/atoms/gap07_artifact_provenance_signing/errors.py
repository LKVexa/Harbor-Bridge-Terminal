"""Stable, machine-readable GAP-07 refusal/failure codes (v6).

Every externally observable refusal is a ``VerificationError`` subclass (or
carries one of these codes).  Callers must branch on ``.code`` - never on the
free-form message text.  The catalogue is exported as ``ERROR_CODES`` so the
compatibility matrix, telemetry and docs are generated from one source.
"""
from __future__ import annotations

from typing import Any, Mapping

from .core import ProvenanceInvalid, SignatureInvalid, SignerUntrusted, Unsigned, VerificationError

# code -> (class of failure, transient?, one-line meaning)
ERROR_CODES: dict[str, tuple[str, bool, str]] = {
    # legacy v5 codes (kept stable)
    "VERIFICATION_FAILED": ("generic", False, "unspecified verification failure (should not be emitted in v6 paths)"),
    "UNSIGNED": ("signature", False, "artifact kind requires a signature and none was supplied"),
    "SIGNATURE_INVALID": ("signature", False, "signature bytes/binding did not verify"),
    "SIGNER_UNTRUSTED": ("trust", False, "signer identity/key is not authorised"),
    "PROVENANCE_INVALID": ("provenance", False, "provenance chain did not verify"),
    # envelopes / parsing
    "ENVELOPE_MALFORMED": ("parse", False, "envelope missing/duplicate/extra/non-canonical fields or bad encoding"),
    "ENVELOPE_VERSION_UNSUPPORTED": ("parse", False, "envelope schema version not accepted (includes PK_SIGNATURE/1)"),
    "INPUT_TOO_LARGE": ("parse", False, "input exceeded a size/depth/count bound before evaluation"),
    # algorithms
    "ALG_UNSUPPORTED": ("crypto", False, "algorithm unknown or forbidden"),
    "ALG_DOWNGRADE": ("crypto", False, "algorithm weaker than the key/identity/policy permits"),
    "ALG_DEPRECATED": ("crypto", False, "algorithm past its deprecation date for this environment"),
    "ALG_REFERENCE_ONLY": ("crypto", False, "reference/test algorithm presented to a production profile"),
    # keys / custody
    "KEY_UNAVAILABLE": ("custody", True, "key provider transiently unavailable (timeout/throttle/outage)"),
    "KEY_DISABLED": ("custody", False, "key disabled, scheduled for deletion or revoked at provider"),
    "KEY_MISMATCH": ("custody", False, "provider response did not match pinned public key/version"),
    "KEY_POLICY_VIOLATION": ("custody", False, "key protection level or algorithm policy not satisfied"),
    "KEY_ID_COLLISION": ("custody", False, "key id not namespace-unique"),
    "CIRCUIT_OPEN": ("custody", True, "provider circuit breaker open"),
    # trust / certificates
    "CHAIN_UNTRUSTED": ("trust", False, "certificate chain does not reach a configured anchor"),
    "CERT_EXPIRED": ("trust", False, "certificate expired"),
    "CERT_NOT_YET_VALID": ("trust", False, "certificate not yet valid"),
    "CERT_REVOKED": ("trust", False, "certificate/key/identity revoked"),
    "CERT_USAGE": ("trust", False, "key usage / EKU / purpose constraint violated"),
    "NAME_CONSTRAINT": ("trust", False, "identity outside issuer name constraints"),
    "PATH_LENGTH": ("trust", False, "chain length/path-length constraint exceeded"),
    "IDENTITY_MISMATCH": ("trust", False, "signer identity does not match credential"),
    "TENANT_MISMATCH": ("trust", False, "cross-tenant/site/environment namespace confusion"),
    "TRUST_ROLLBACK": ("trust", False, "lower/equal trust generation offered"),
    "TRUST_STALE": ("trust", True, "trust state older than its staleness budget"),
    "TRUST_CORRUPT": ("trust", False, "persisted trust state failed digest/signature/schema checks"),
    "TRUST_SCOPE": ("trust", False, "trust object scoped to another tenant/site/environment"),
    "TRUST_PARENT_MISMATCH": ("trust", False, "delta parent generation does not match active generation"),
    "TRUST_NOT_LOADED": ("trust", True, "no verified trust generation is active"),
    # time
    "TIME_UNTRUSTED": ("time", True, "no time source satisfies policy uncertainty/trust"),
    "TIME_STALE": ("time", True, "last trusted time sync exceeded offline budget"),
    "CLOCK_ROLLBACK": ("time", False, "wall clock moved behind persisted trusted floor"),
    "CLOCK_JUMP": ("time", False, "implausible forward clock jump detected"),
    "SIGNATURE_EXPIRED": ("time", False, "signature exceeded maximum age"),
    "SIGNATURE_FUTURE": ("time", False, "signature issued in the future beyond skew"),
    # attestations
    "ATTESTATION_INVALID": ("attestation", False, "DSSE/in-toto/SLSA structure or signature invalid"),
    "ATTESTATION_SUBJECT": ("attestation", False, "subject digest does not exactly match artifact"),
    "ATTESTATION_PREDICATE": ("attestation", False, "predicate type not allowed"),
    "ATTESTATION_BUILDER": ("attestation", False, "builder identity/build type not allowed"),
    "ATTESTATION_MATERIALS": ("attestation", False, "materials/parameters violate policy"),
    "ATTESTATION_CONFLICT": ("attestation", False, "contradictory attestations for one subject"),
    # transparency
    "TLOG_REQUIRED": ("transparency", False, "policy requires transparency evidence and none supplied"),
    "TLOG_PROOF_INVALID": ("transparency", False, "inclusion or consistency proof did not verify"),
    "TLOG_CHECKPOINT_INVALID": ("transparency", False, "checkpoint signature / log key invalid"),
    "TLOG_CHECKPOINT_STALE": ("transparency", True, "checkpoint older than staleness budget"),
    "TLOG_ROLLBACK": ("transparency", False, "smaller/older or inconsistent tree head offered"),
    "TLOG_ENTRY_MISMATCH": ("transparency", False, "log entry does not bind the evaluated signature"),
    "TLOG_UNAVAILABLE": ("transparency", True, "transparency service unavailable"),
    # policy
    "POLICY_DENY": ("policy", False, "policy rule denied admission"),
    "POLICY_NO_MATCH": ("policy", False, "no policy rule matched; default deny"),
    "POLICY_CONFLICT": ("policy", False, "conflicting rules at equal priority; deny"),
    "POLICY_INVALID": ("policy", False, "policy bundle unsigned/corrupt/incompatible/stale"),
    "POLICY_UNAVAILABLE": ("policy", True, "no active verified policy bundle"),
    "THRESHOLD_UNMET": ("policy", False, "M-of-N distinct signer threshold not met"),
    "EXCEPTION_INVALID": ("policy", False, "waiver unsigned, expired, or out of scope"),
    # SBOM
    "SBOM_INVALID": ("sbom", False, "SBOM malformed or not bound to artifact"),
    "SBOM_POLICY": ("sbom", False, "SBOM package/vulnerability policy violated"),
    # registry
    "REGISTRY_MALFORMED": ("registry", False, "OCI manifest/index/descriptor malformed"),
    "REGISTRY_DIGEST_MISMATCH": ("registry", False, "content digest does not match descriptor"),
    "REGISTRY_MEDIA_TYPE": ("registry", False, "media type unsupported"),
    "REGISTRY_UNAVAILABLE": ("registry", True, "registry/content store read failed"),
    "MUTABLE_REFERENCE": ("registry", False, "tag/name presented where immutable digest required"),
    # admission
    "NOT_READY": ("admission", True, "verifier not ready (trust/policy/time/tlog dependency)"),
    "OVERLOADED": ("admission", True, "verification capacity exhausted; request shed (deny)"),
    "QUARANTINED": ("admission", False, "artifact digest is quarantined"),
    "REPLAY": ("admission", False, "nonce/authorisation already used"),
    "TOCTOU": ("admission", False, "handoff bytes differ from verified digest"),
    "BREAK_GLASS_INVALID": ("admission", False, "break-glass authorisation invalid"),
    "INTERNAL_ERROR": ("admission", False, "unexpected defect; treated as deny"),
    # audit
    "AUDIT_CHAIN_BROKEN": ("audit", False, "exported audit chain gap/reorder/tamper"),
    "AUDIT_SPOOL_FULL": ("audit", True, "audit spool full; security operations blocked"),
}


class GapError(VerificationError):
    """v6 refusal carrying an explicit catalogue code."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None):
        if code not in ERROR_CODES:
            raise ValueError(f"unregistered GAP-07 error code {code!r}")
        super().__init__(message, details=details)
        self.code = code

    @property
    def transient(self) -> bool:
        return ERROR_CODES[self.code][1]


def fail(code: str, message: str, **details: Any) -> GapError:
    """Build (not raise) a GapError - ``raise fail(...)``."""
    return GapError(code, message, details=details)


__all__ = [
    "ERROR_CODES", "GapError", "fail", "VerificationError", "Unsigned",
    "SignatureInvalid", "SignerUntrusted", "ProvenanceInvalid",
]
