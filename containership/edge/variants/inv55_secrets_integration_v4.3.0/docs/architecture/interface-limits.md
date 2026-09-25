# Interface limits

| ID | INV55-ARCH-LIMITS | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Limit | Value | Symbol | On breach |
|---|---|---|---|
| Identifier (name, app) | regex `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$` (1–256 chars), no empty/`.`/`..` segments | `service.py::_ID`, `valid_path_segments` | INVALID_REFERENCE |
| request_id | `[A-Za-z0-9_-]{1,64}` | `SecretsService._run` | replaced with random id |
| Request type | must be a `dict` | `_run` | INVALID_REFERENCE |
| Protocol version digits | 1–3 | `negotiate` | UNSUPPORTED_VERSION |
| Secret value size | 65 536 bytes (UTF-8) | `ServiceLimits.max_secret_bytes` | LIMIT_EXCEEDED |
| Apps per scope | 1 024 | `max_apps_per_scope` | LIMIT_EXCEEDED |
| Active leases | 100 000 | `max_active_leases` | OVERLOADED |
| Leases per subject | 1 000 | `max_leases_per_subject` | QUOTA_EXCEEDED |
| Default lease TTL | 300 s | `lease_ttl_s` | — |
| Max lease TTL | 3 600 s (silently capped) | `max_lease_ttl_s` | — |
| Cache TTL | 30 s | `cache_ttl_s` | — |
| Stale grace | 0 s | `stale_grace_s` | — |
| Request timeout | 2.0 s (caller `timeout_ms` clamped to [1 ms, 2 s]) | `request_timeout_s` | DEADLINE_EXCEEDED |
| Stall detection | 30 s | `stall_after_s` | health ready=false |
| Idempotency key | `[A-Za-z0-9_-]{8,64}` | `rotate` | INVALID_REFERENCE |
| Idempotency cache | 100 000 entries keyed `tenant/name/key`; evicts only completed entries | `rotate` | OVERLOADED if all entries are pending |
| In-flight requests | 256 | `AdmissionController.max_in_flight` | OVERLOADED |
| Tenant rate/burst | 200/s, 400 | `tenant_rate/burst` | QUOTA_EXCEEDED |
| Workload rate/burst | 50/s, 100 | `workload_rate/burst` | QUOTA_EXCEEDED |
| Tracked bucket keys | 10 000 (authenticated tenants/workloads) | `max_tracked_keys` | OVERLOADED |
| Retry attempts | 3 (allowed 1–10), base 0.05 s, cap 1.0 s | `RetryPolicy` | last error |
| Circuit breaker | 5 consecutive retryable failures, 5 s cooldown | `CircuitBreaker` | PROVIDER_UNAVAILABLE |
| Token `tenant` claim | `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` | `HmacJwtAuthenticator` | UNAUTHENTICATED |
| Token `sub` claim | `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$` | same | UNAUTHENTICATED |
| Token `roles` | list of ≤ 16 strings | same | UNAUTHENTICATED |
| Workload token size | 8 192 bytes | `HmacJwtAuthenticator.max_token_bytes` | UNAUTHENTICATED |
| Token clock leeway | 30 s | `leeway_s` | — |
| Vault response body | 1 048 576 bytes | `vault.py::MAX_RESPONSE_BYTES` | ProviderError → PROVIDER_UNAVAILABLE |
| Vault HTTP timeout | 2.0 s per call | `VaultProvider.timeout_s` | ProviderUnavailable |
| Vault token renew point | 0.67 × TTL | `renew_fraction` | re-login |
| Metric series | 2 000 | `Metrics(max_series)` | series dropped, `dropped_series`++ |
| Metric label value | `^[A-Za-z0-9_.:-]{1,64}$` | `telemetry.py::_LABEL_OK` | ValueError |
| Finished spans kept | 10 000 | `Tracer(max_spans)` | oldest dropped |
| Decision ledger | 10 000 | `DecisionLedger(limit)` | oldest dropped |
| Config history | 10 generations | `ConfigController.history_limit` | oldest dropped |
| Config errors reported | 20 | `ConfigController.activate` | truncated |

Not bounded / NOT IMPLEMENTED: number of scopes, retired-version set, cache entries (bounded only by distinct tenant/name pairs), Vault connection pool (a new urllib connection per call).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Path segments, claim limits, idempotency eviction |
| 4.3.0 | 2026-09-22 | Idempotency scope, request type, admission keys |
