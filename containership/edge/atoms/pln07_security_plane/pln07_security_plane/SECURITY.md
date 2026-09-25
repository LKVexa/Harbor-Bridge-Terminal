# PLN-07 Security Model — v4.3.0

## Security objective

PLN-07 must never create or accept authority that is broader than the authority explicitly issued to the caller. A verifier must fail closed when a grant is expired, revoked, malformed, over-deep, cross-tenant, outside the requested capability, or—when signature enforcement is enabled—unsigned or cryptographically invalid.

## Trust boundaries

The grant object is not an identity provider, policy engine, key-management service, trusted-clock source, or runtime enforcement point. Production verification therefore depends on authenticated identity from GAP-06, authorization from GAP-13, cryptographic trust material from GAP-07, trustworthy time, revocation distribution, and enforcement in the runtime/execution planes.

## Threats and controls in this package

| Threat | v4.3.0 control | Residual dependency/gap |
|---|---|---|
| Scope widening | Constructor and attenuation subset checks; verifier rechecks every link | None for the in-memory model |
| Expiry extension | Child expiry cannot exceed parent; every link is checked | Trusted time source is external |
| Cross-tenant chain | Constructor and verifier reject tenant changes | Environment/site/workload boundaries are not first-class grant fields |
| Delegation explosion | Maximum depth of 5, checked on construction and verification | Policy-specific depth limits are not configurable |
| Revoked ancestor reuse | Every ancestor ID is checked against the verifier revocation set | Durable propagation and revocation-horizon service are external |
| Grant-chain cycle | Cycle detection in identifier and verification paths | Deliberate memory corruption is outside this module |
| Post-issue payload editing | Canonical payload plus optional required signature verification | Concrete signing/trust root comes from GAP-07 |
| Ambiguous/unbounded inputs | Type, length, scope cardinality, control-character, integer, and skew validation | Host/API transport size limits remain external |
| Optimized-mode check removal | Security tests pass under `python -O`; checks do not use runtime `assert` in production logic | Framework integration still requires external `pk_core` |
| Identifier collision | Full SHA-256 `fingerprint` is available for audit correlation | Legacy 16-hex `id` remains for 4.x revocation compatibility and is not a full cryptographic identifier |

## Fail-closed requirements

Production callers should construct `Verifier(require_signatures=True, signature_verifier=...)`. If signature verification is required and no verifier is supplied, construction fails. Unsigned grants and signature-verifier failures are rejected. Callers must not treat `require_signatures=False` as production authorization unless a higher layer provides equivalent cryptographic authenticity.

A caller must also supply a trustworthy logical/current time to `verify`. This module validates the value but cannot establish that the time source itself is trustworthy.

## Added in 4.3.0

| Threat | 4.3.0 control | Test |
|---|---|---|
| Post-issue tampering / stripped signature | `PK_SIG/1` over canonical body, domain+kid+alg bound | ThreatSuite.test_tamper_scope_after_issue / test_strip_signature |
| Issuer spoofing | trust-domain separation, pinned key ids | ThreatSuite.test_spoof_issuer_domain |
| Replay to another service | `audience` boundary, per-issue nonce | ThreatSuite.test_replay_to_other_audience / test_nonce_unique_across_issues |
| Clock manipulation | TrustedClock quorum, rollback detection | TrustedTimeTest |
| Revocation loss on crash | fsync'd hash-chained log, replay | RevocationTest |
| Stale controller / split brain | epoch fencing | RevocationTest.test_stale_epoch_fenced |
| Resource exhaustion | admission control, wire bounds, 64 KiB body cap, cardinality caps | ThreatSuite.test_resource_exhaustion_inputs / test_admission_sheds_floods |
| Control-plane abuse | authenticated issue/revoke, holder-only attenuate, loopback admin | ServiceContractTest |
| Secret leakage in diagnostics | redaction in logs/audit/config describe | ObservabilityTest, ConfigTest |
| Collision on 16-hex ids | revocation keyed by full fingerprint | GrantV2Test.test_fingerprint_revocation |

## Known non-implemented controls (4.2.0 list, updated)

Still external in 4.3.0: production identity provider/hardware attestation (GAP-06), production policy engine (GAP-13), HSM/KMS key custody (GAP-07), inter-site revocation transport (GAP-04), runtime sandbox enforcement and VM/CHERI/SFI/Spectre controls (PLN-01/03/04). The package ships reference implementations and protocols for the first four.

## Original 4.2.0 note

PLN-07 v4.3.0 does not provide identity provisioning, policy evaluation, hardware attestation, key storage/rotation, cryptographic algorithm selection, revocation transport, durable state, runtime sandbox enforcement, VM/CHERI/SFI/Spectre controls, telemetry pipelines, incident automation, or deployment orchestration. See `MISSING_COMPONENTS.md` for the complete production-gap inventory.
