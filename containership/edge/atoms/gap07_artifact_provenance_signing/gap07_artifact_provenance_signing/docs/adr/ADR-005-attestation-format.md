# ADR-005: Attestation format
Status: accepted
Decision: DSSE v1 + in-toto Statement v1. SLSA Provenance v1 is validated natively. CycloneDX 1.4-1.6 and SPDX 2.3 are accepted as predicates. Signer authority is per predicate type (`attest:<predicateType>` usage). New predicate versions need explicit policy enablement.
Follow-up: M-of-N signing for config-authority documents (threat T5) is recommended for v6.1.
