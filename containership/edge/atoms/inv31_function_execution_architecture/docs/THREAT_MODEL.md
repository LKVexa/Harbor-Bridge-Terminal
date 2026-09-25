# INV-31 Threat Model (C041, C050, C087)

| Threat (STRIDE) | Control | Test |
|---|---|---|
| Spoofed caller (S) | HMAC-SHA256 assertions, keys ≥32 bytes, injected | `AuthenticationTest::test_forged_signature_refused` |
| Replayed assertion (S/R) | nonce cache, bounded lifetime ≤600 ticks | `test_replay_refused` |
| Claim tampering (T) | signature over canonical JSON | `test_tampered_claims_refused` |
| Cross-tenant invocation (E) | tenant-bound principal + `invoke:<tenant>` | `test_cross_tenant_invoke_denied` |
| Cross-tenant memory reuse (I) | exact tenant/version reuse rule | `ConcurrencyStressTest`, fuzz |
| Service self-escalation to operator actions (E) | disable/config require human/operator kind | `test_service_cannot_emergency_disable`, `ConfigTest` |
| Audit tampering (R) | SHA-256 hash chain | `test_audit_chain_detects_tampering` |
| Resource exhaustion (D) | pool ceiling, tenant quota/share, bounded caches/logs | `QuotaFairnessTest`, `test_telemetry_overflow_is_counted_not_silent` |
| Hostile input (T/D) | identifier validation, strict schemas | `test_hostile_assertions_never_raise`, `test_hostile_requests_never_raise` |
| Tenant data in telemetry (I) | pseudonymous tenant handles, tenant-free health | `ObservabilityTest` |
| Clock rollback (T) | negative-age eviction; future-issued assertions refused | runtime + `test_expired_future_and_overlong_refused` |
| Supply chain (T) | stdlib-only runtime; SBOM + digests in evidence | `evidence/sbom.json` |

Not covered (out of scope or BLOCKED): side channels between co-resident instances
(PLN-04 isolation tier), sandbox escape (PLN-04), encryption in transit/at rest (C047 —
no data leaves the process; key management requires a KMS that was not supplied),
artifact signature verification of function code (C045 — belongs to the code loader).
