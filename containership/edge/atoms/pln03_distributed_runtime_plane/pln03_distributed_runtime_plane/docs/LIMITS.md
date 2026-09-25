# Resource limits, quotas and fairness (MC-008, MC-017)

All values are fields of `resilience.Limits`, configurable only through validated config (`config.validate` rejects non-positive values and inconsistent combinations).

| Limit | Default | Scope | On breach |
|---|---|---|---|
| max_inline_bytes | 1 MiB | payload/value | `PK_PAYLOAD_TOO_LARGE` (bulk goes to PLN-06) |
| max_key_chars | 1024 | key/reference | `PK_INVALID_ARGUMENT` |
| max_transaction_ops | 128 | transaction | `PK_INVALID_ARGUMENT` |
| wire MAX_REQUEST_BYTES | 2 MiB | serialized request | `PK_INVALID_ARGUMENT` before parse |
| max_concurrency_global | 256 | process | `PK_RATE_LIMITED` (load shed) |
| max_concurrency_per_tenant | 32 | tenant | `PK_QUOTA_EXCEEDED` |
| rate_per_tenant_per_s / burst_per_tenant | 500 / 1000 | tenant | `PK_RATE_LIMITED` |
| max_tenants_tracked | 10 000 | process | `PK_QUOTA_EXCEEDED` |
| max_offline_buffer_msgs / max_offline_buffer_bytes | 10 000 / 64 MiB | site | `PK_READ_ONLY` |
| max_audit_events_in_memory | 100 000 | process ring (file sink unbounded, rotated by ops) | oldest evicted from memory only |
| metrics MAX_SERIES | 5 000 | process | series dropped, `dropped_series` counted |
| default_deadline_s / max_deadline_s | 2 s / 30 s | call | `PK_DEADLINE_EXCEEDED` |
| retry_max_attempts / retry_budget_ratio (backoff retry_base_s, retry_cap_s) | 4 / 20 % (20 ms, 1 s) | call / process | original error surfaced |
| token max TTL / size | 3600 s / 4096 chars | token | `PK_TOKEN_INVALID` |
| state_quota_bytes_per_tenant | 256 MiB | tenant | **declared, not yet enforced** — requires adapter-side accounting (open) |

**Fairness:** a tenant can hold at most `max_concurrency_per_tenant / max_concurrency_global` of the pool (default 12.5 %); refused requests do not consume that tenant's rate tokens (fixed in 4.3.0 — see CHANGELOG).
| breaker_failure_threshold / breaker_reset_s | 5 / 5 s | adapter | `PK_CIRCUIT_OPEN` |
