"""Binding contract for GAP-07 - Artifact provenance/signing."""
from __future__ import annotations

from pk_core.contract import Contract, Dependency, Slo

ELEMENT_ID = "GAP-07"
ELEMENT_NAME = "Artifact provenance/signing"


def build() -> Contract:
    """Return the production contract for GAP-07."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own artifact signing and verification: bind every executable or policy artifact to its digest, "
            "artifact kind, environment, key identity and trusted signer; record a verifiable provenance chain; "
            "and refuse unsigned, malformed, mis-signed, stale-by-policy, revoked, or digest-mismatched input."
        ),
        owns=[
            "Trusted signer metadata and revocation state",
            "Versioned artifact signature/verification formats",
            "Digest, artifact-kind and environment binding",
            "Signer and verification-key revocation/rotation semantics",
            "Verifiable provenance hash chains",
            "Local tamper-evident security-event chaining",
        ],
        not_owns=[
            "Production private-key custody or generation",
            "What an artifact does once admitted",
            "Node attestation",
            "Policy authorship",
            "Artifact transport",
            "External transparency-log operation",
        ],
        dependencies=[
            Dependency("GAP-13 Policy engine", "upstream", "Declares which artifact kinds require which signers and freshness rules"),
            Dependency("GAP-06 Device identity and attestation", "downstream", "Uses signing primitives for attestation evidence"),
            Dependency("GAP-08 OTA lifecycle/rollback", "downstream", "Admits only signed update bundles"),
            Dependency("PLN-07 Security plane", "downstream", "Signs capability grants with these primitives"),
            Dependency("PLN-06 Data plane", "downstream", "Signs data classification labels"),
            Dependency("Estate KMS/HSM", "upstream", "Holds production signing/verification key material outside this component"),
        ],
        source_of_truth=(
            "The environment-scoped trust store for signer/role/key acceptance and revocation, plus the external key provider for key material."
        ),
        assumptions=[
            "Production key material is held by a KMS/HSM or equivalent provider outside this component",
            "A signer or individual verification key may be revoked after artifacts were already deployed",
            "Disconnected sites may carry a cached trust store subject to an explicit staleness policy",
            "Callers supply trusted time when enforcing signature maximum-age policy",
        ],
        boundaries={
            "tenant": "tenants may have their own signers but never sign estate-wide artifacts",
            "environment": "signatures and trust stores are environment-bound and do not promote automatically",
            "site": "a site may hold a cached trust store with a policy-defined staleness bound",
            "workload": "each workload artifact carries or references its own signature and provenance record",
        },
        mandatory=[
            "Bind each signature to environment, artifact kind, signer, key id, issuance time and artifact digest",
            "Verify against a signer/key currently accepted and unrevoked in the local trust store",
            "Refuse unsigned executable or policy artifacts",
            "Reject digest, role, kind, environment, key or authentication-tag mismatches",
            "Record and verify a metadata-bound provenance hash chain for admitted artifacts",
            "Emit tamper-evident local security events for trust and verification operations",
        ],
        optional=[
            "Multi-signature thresholds for high-risk artifacts",
            "Transparency-log inclusion proofs",
            "Counter-signing by an independent reviewer",
            "Maximum signature-age enforcement when trusted time is available",
        ],
        non_goals=[
            "Generating or persistently storing production private keys",
            "Judging artifact behaviour",
            "Attesting nodes",
            "Guaranteeing revocation reaches a partitioned site instantly",
            "Operating an external transparency service",
        ],
        interfaces={
            "sign": "PK_SIGNATURE/2 - kind/environment/key/digest-bound signature envelope",
            "verify": "PK_VERIFICATION/2 - structured verification result/refusal",
            "trust": "PK_TRUST_STORE/2 - accepted signer roles, key ids, rotation and revocation",
            "provenance": "PK_PROVENANCE/2 - metadata-bound provenance hash chain",
            "audit": "PK_AUDIT_EVENT/1 - local hash-chained security events",
        },
        threats=[
            "Byte substitution under a valid signature",
            "Cross-kind or cross-environment signature replay",
            "A revoked signer or retired key continuing to authorize artifacts",
            "Trust-store poisoning or silent signer-role replacement",
            "Signature stripping followed by unsigned admission",
            "Role confusion: a data signer authorizing executable code",
            "Provenance step editing/reordering without detection",
            "Malformed envelopes causing fail-open behavior",
        ],
        failure_modes=[
            "Digest mismatch between signature and bytes",
            "Signer absent from or revoked in the trust store",
            "Verification key retired or unavailable",
            "Artifact kind requires a role the signer does not hold",
            "Signature envelope kind/environment/schema/algorithm mismatch",
            "Signature age violates a caller-supplied freshness policy",
            "Provenance chain or linked payload digest fails verification",
        ],
        slos=[
            Slo("verification soundness", "zero artifacts admitted whose signed envelope or digest does not verify", "no budget"),
            Slo("revocation", "zero artifacts admitted from a locally revoked signer or retired key", "no budget"),
            Slo("verification latency", "p99 verification under 2ms for reference-size metadata after artifact hashing", "1% may exceed"),
        ],
        signals={
            "verifications": "counter by artifact kind and outcome",
            "digest_mismatches": "counter of byte-substitution attempts caught",
            "replay_refusals": "counter of kind/environment replay attempts caught",
            "revoked_signer_use": "counter of artifacts refused for a revoked signer or key",
            "trust_store_age_seconds": "gauge of local trust-store staleness",
            "unsigned_refusals": "counter of unsigned artifacts refused",
            "audit_chain_health": "boolean/integrity result for the local security-event chain",
        },
    )
