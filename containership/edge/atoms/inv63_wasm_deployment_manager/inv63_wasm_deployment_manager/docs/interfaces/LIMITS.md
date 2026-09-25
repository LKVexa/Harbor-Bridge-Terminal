# INV-63 interface limits (INV-63-C028)

Every limit below is enforced in code and exercised by tests; the test
`test_documented_limits_are_enforced` fails if the numbers drift.

| Limit | Value | Enforced in | On breach |
|---|---|---|---|
| Wire payload size | 65536 bytes (`MAX_PAYLOAD_BYTES`) | `schema.parse_bytes` | `INV63-E-PAYLOAD-TOO-LARGE` |
| JSON nesting depth | 8 (`MAX_DEPTH`) | `schema._validate` | `INV63-E-SCHEMA` |
| Identifier length | 256 chars | schemas + `manager._validate_identifier` | `INV63-E-SCHEMA` / `INV63-E-INVALID-REQUEST` |
| Desired count | 0..1000 per component | `PK_DEPLOY_DESIRED/*` | `INV63-E-SCHEMA` |
| Diff actions | <= 2000 start, <= 2000 stop | `PK_DEPLOY_DIFF/1` | `INV63-E-SCHEMA` |
| Concurrent requests | `max_inflight` (default 64) | `resilience.Admission` | `INV63-E-OVERLOADED` (critical priority exempt) |
| Batch-priority shedding | above 80% of `max_inflight` | `resilience.Admission` | `INV63-E-OVERLOADED` |
| Per-tenant rate | 50 req/s, burst 100 | `resilience.Admission` | `INV63-E-QUOTA` |
| Queue depth | `queue_depth` (default 1024) for async integrations; the synchronous `handle` path is bounded by `max_inflight` instead | `resilience.Admission.enqueue` | `INV63-E-OVERLOADED` |
| Tenant instance quota | `tenant_quotas.<t>.max_instances` | `service.op_set_desired` | `INV63-E-QUOTA` |
| Request timeout | `request_timeout_ms` (default 5000, max 300000) | `service.handle` | `INV63-E-DEADLINE` |
| Retry attempts | `retry_max_attempts` (default 4, max 10) | `resilience.RetryPolicy` | last error surfaced |
| Circuit breaker | opens after `circuit_failure_threshold` (default 5), resets after 10 s | `resilience.CircuitBreaker` | `INV63-E-CIRCUIT-OPEN` |
| Idempotency cache | 10000 keys (LRU) + journaled | `service.handle` | oldest evicted |
| Token replay window | 100000 nonces | `security.TokenAuthority` | `INV63-E-REPLAY` |
| Metric series | 2000 label sets per store (counters / gauges / histograms, across all names) | `observability.Metrics` | series dropped + counted |
| Histogram samples | 10000 per series (decimated) | `observability.Metrics` | decimation |
| Journal size | 256 MiB before compaction | `store.Journal.append` | `INV63-E-QUOTA` |
| Connections | one injected lattice transport | `adapter` | n/a |
