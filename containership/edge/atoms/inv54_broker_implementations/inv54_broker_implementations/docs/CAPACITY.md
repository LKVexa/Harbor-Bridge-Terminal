# Capacity, quota and fairness model  (C017, C028, C067, C069 · components 08, 65, 68, 70)

Every growth path is bounded twice: a configured limit and a hard ceiling (`config.HARD_LIMITS`, `resilience.HARD_*`).

| Resource | Config | Hard ceiling | Overload behaviour |
|---|---|---|---|
| message size | `limits.max_message_bytes` | 16 MiB | `INV54-E0001` |
| subscribers per tenant | `limits.max_subscribers_per_tenant` | 100k | `INV54-E0204` |
| subscriber backlog | `limits.max_backlog_per_subscriber` | 10M | `reject` (all-or-nothing) or `drop_oldest` (DEGRADED + counter) |
| records per partition | `limits.max_log_records_per_partition` | 1e9 | `INV54-E0204` until retention runs |
| in-flight requests | `limits.max_inflight` | 100k | priority shedding at 80 %, hard shed at 100 % (`INV54-E0202`) |
| idempotency keys | cache capacity | 1M | LRU eviction (documented dedup horizon) |
| per-(tenant,workload) rate | `quotas.*.publish_rate/burst` | — | `INV54-E0201` |
| per-tenant retained bytes | `quotas.*.max_bytes` | — | `INV54-E0201` |
| label cardinality | `telemetry.max_label_values` | — | folded into `__overflow__` |

**Fairness:** each (tenant, workload) has its own token bucket and byte budget; exhaustion is local.
**Saturation signal:** `quota.saturation()` = max(inflight util, backlog util) → ok < 0.7 ≤ warning < 0.9 ≤ saturated; `ready=false` when saturated.
