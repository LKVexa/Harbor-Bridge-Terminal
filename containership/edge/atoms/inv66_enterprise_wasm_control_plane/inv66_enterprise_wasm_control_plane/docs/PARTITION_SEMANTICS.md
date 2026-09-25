# Offline / partition semantics (MC-010, MC-040)

Each dependency is classified, and the control plane's behaviour when it is unavailable is
specified. Every row is exercised by a test.

| Dependency | Class | When unavailable | Cache / staleness | Reason code | Test |
|---|---|---|---|---|---|
| Journal (audit store) | durability- and security-critical | **No admissions at all**; the plane goes not-ready; read paths serve from projections | none | `ECP_AUDIT_UNAVAILABLE` | `test_journal_failure_admits_nothing_and_degrades` |
| Identity (JWKS / trust material) | security-critical | New requests can't authenticate, so they fail closed | static JWKS pinned in config; live refresh is an adapter slot with **no** stale extension | `ECP_UNAUTHENTICATED` | `IdentityTest.*` |
| Config generation | security-critical | No active generation means every admission fails | none | `ECP_DEPENDENCY_UNAVAILABLE` (dependency=config) | `_policy()` |
| GAP-13 policy engine | security-critical when `engine=external` | `on_unavailable=deny` (default) → deny. `use_cached` → only an identical-input answer younger than `cache_ttl_s` | TTL ≤ 3600 s by schema. **Only positive answers are cached**, and a version mismatch is never cached | `ECP_DEPENDENCY_UNAVAILABLE` / `ECP_POLICY_DENIED` | `test_policy_engine_down_fails_closed_or_uses_fresh_cache`, `test_policy_engine_outage_fails_closed` |
| Registry resolver (optional) | security-critical if configured | Digest not confirmed → deny | none | `ECP_PROVENANCE_INVALID` | `ProvenanceTest.test_registry_resolver` |
| Signer trust (config) | security-critical | Part of the config generation: revoked/expired → deny | `not_after` enforced against the clock | `ECP_SIGNER_NOT_APPROVED` | `test_revoked_and_expired` |
| INV-63 deployment manager | availability-enhancing | Admission still decides and journals, then goes to `delivery_pending`. Redelivered on reconnect with the same decision id | n/a | `ECP_DELIVERY_FAILED` (internal), breaker `ECP_CIRCUIT_OPEN` | `test_partition_from_deployment_manager_then_reconnect` |
| SIEM sink | optional | The checkpoint doesn't advance. After `max_failures` failed runs a dead-letter record is written. Nothing is skipped | durable checkpoint | `ECP_DEPENDENCY_UNAVAILABLE` (siem) | `test_siem_export_checkpoint_retry_dedupe` |
| Lease store (HA) | durability-critical | A replica without the lease can't write | lease TTL | `ECP_NOT_LEADER` | `test_site_loss_failover_with_fencing` |
| Clock | assumption | Token `exp`/`nbf` checks use ±`skew_s` (30 s). Lease expiry assumes bounded drift between replicas smaller than the TTL | — | — | `IdentityTest` |

## During a partition

- **Workloads admitted before the partition keep running.** INV-63 and wasmCloud own the runtime, and INV-66 never revokes running work on its own initiative.
- **New admissions are blocked** at any site that can't reach the journal leader. There is no local-autonomy admission mode (unsupported, ADR-0001).
- **Administrative changes are blocked** under the same rule (they are journal writes).
- **Reconnect:** followers `refresh()` from the shared journal, pending deliveries are resumed, and duplicates are removed by the decision-id idempotency key at INV-63.

## Operator-visible degraded state

`/readyz` returns `ready=false` with `mode ∈ {normal, degraded, frozen}` and a per-dependency
`status`, `since` and `last_error`. `ecp_breaker_open{dependency}` and `ecp_delivery_pending` are exported.
