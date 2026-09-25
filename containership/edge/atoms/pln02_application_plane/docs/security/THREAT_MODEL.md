# PLN-02 threat model (MC-19, C041, C050, C087)

Method: STRIDE per trust boundary. Every mitigation cites the code and the test that exercises it.

## Assets
A1 published revisions · A2 provider bindings · A3 signed catalogue · A4 trust keys (catalogue/token/audit/artifact) ·
A5 audit ledger · A6 configuration/entitlements · A7 tenant composition data · A8 availability of publication.

## Trust boundaries
B1 caller → service (`submit`, `admin`) · B2 INV-65 catalogue source → client · B3 cache on disk → client ·
B4 service → store filesystem · B5 service → audit file · B6 config source → ConfigManager ·
B7 OAM/WIT text → parsers · B8 revision store → PLN-03/SCH-01 consumers · B9 GAP-04 lease → catalogue client.

## Attacker models
M1 malicious tenant with valid token · M2 unauthenticated network caller · M3 compromised provider/INV-65 feed ·
M4 host user with store-directory write access · M5 stale/partitioned controller · M6 insider with config write.

## Threats → mitigations → tests
| # | Threat (STRIDE) | Boundary | Mitigation | Test |
|---|---|---|---|---|
| T1 | Spoofed caller (S) | B1 | HMAC/Ed25519 bearer tokens, audience, TTL ≤ 900 s, skew 30 s, key revocation | `MC11Authentication.*` |
| T2 | Capability not entitled — contract threat 1 (E) | B1 | `EntitlementPolicy.authorize_resolve` before catalogue access | `MC12Entitlement.test_denials`, `test_authn_authz_errors_are_public_documents` |
| T3 | Cross-tenant access (I/E) | B1/B4 | principal.tenant must equal ctx.tenant; store paths tenant-scoped | `MC12Entitlement`, `MC13Context` |
| T4 | Provider substitution between resolution and execution — contract threat 2 (T) | B8 | content address covers bindings; `provider_binding_digest`; consumers `verify_revision` | `test_pln01_to_pln03_and_sch01`, `test_crash_leftovers_and_corruption_recovered` |
| T5 | Interface type confusion — contract threat 3 (T) | B7 | exact version match; WIT structural checker | `MC10WIT.*`, resolver suite |
| T6 | Catalogue poisoning — contract threat 4 (T) | B2/B3 | signature, scope binding, generation monotonicity, tampered cache ignored | `test_poisoned_catalogue_rejected`, `test_cache_survives_restart_and_tampered_cache_ignored` |
| T7 | Revision identity collision — contract threat 5 (T) | core | full SHA-256 over normalized specs | `test_semantic_change_changes_identity` |
| T8 | Catalogue replay / rollback (T) | B2 | generation monotonic; expiry | `test_partition_with_gap04_lease_degrades_then_reconnects` |
| T9 | Token replay (S) | B1 | short TTL; idempotency key scoped to tenant | `MC11`, `MC13Context.test_idempotency` |
| T10 | Split-brain double publication (T) | B4 | fencing epoch | `test_split_brain_fencing` |
| T11 | Audit tampering / truncation (R) | B5 | hash chain + MAC + anchored head | `MC22Audit.test_chain_tamper_truncate_restart` |
| T12 | Injection / parser DoS (D) | B1/B7 | payload bound before parse; bounded depth/items; fuzzed | `MC05Admission`, `test_fuzz_property.*` |
| T13 | Resource exhaustion by one tenant (D) | B1 | token bucket, per-tenant + global concurrency, shedding, bounded caches | `MC05Admission.*`, `test_concurrent_submissions_consistent` |
| T14 | Secret leakage via errors/logs/metrics (I) | all | `to_public` allow-lists; `redact`; label sanitisation; no inline secrets | `MC14Errors`, `MC18Secrets`, `MC30Observability` |
| T15 | Unsigned / unapproved provider artifact (T/E) | B2 | `verify_artifact`: signature, approved version, revocation | `MC21SupplyChain` |
| T16 | Stale partitioned site keeps authority (E) | B9 | lease + max offline window; signatures verified offline | `test_partition_without_lease_fails_closed`, `test_offline_window_bound` |
| T17 | Malicious config weakens policy (T) | B6 | strict schema, bounds, lower sources cannot widen, provenance digest, LKG rollback | `MC17Config.*`, `MC07MC28Policy.test_lower_source_cannot_weaken` |
| T18 | Timing side channel on MAC compare (I) | B1/B5 | `hmac.compare_digest` | code review |

## Residual risk (owned in `registers/TECH_DEBT.json`)
- HMAC catalogue keys are symmetric (TD-002). - Store is single-writer per root (TD-001).
- Host user with write access to store *and* audit key can forge history: mitigated only by OS isolation
  (ISOLATION_PROFILE) and external anchoring of the audit head.
- Side channels beyond MAC comparison (cache timing, co-tenancy) are out of scope of this package.

## Unavailable-dependency behaviour (C048)
Identity/keys unavailable → `UNAUTHENTICATED` (never allow). Catalogue unavailable → `CATALOGUE_STALE` unless
leased. Secret store unavailable → `SECRET_UNAVAILABLE`. Time: tokens use wall clock with 30 s skew; a clock
jump beyond skew fails closed.
