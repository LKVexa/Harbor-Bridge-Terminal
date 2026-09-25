# ADR-001: Production signing stack
Status: accepted (v6.0.0) - pending independent review
Decision: native `PK_SIGNATURE/3` envelopes with Ed25519 (default), ECDSA P-256/P-384 and RSA-PSS ≥ 3072, all via `cryptography`/OpenSSL. HMAC is kept only as an isolated reference profile.
Why: GAP-07 needs explicit binding of tenant, site, environment, kind, purpose and policy domain, plus namespace-qualified key ids. Neither cosign's simple signing payload nor bare DSSE provides that binding. DSSE is still used for attestations (ADR-005), and a Sigstore bridge can sit behind `KeyCustody` + `trust.validate_x509`.
Consequences: other verifiers must implement `ld_encode` (vectors provided).
