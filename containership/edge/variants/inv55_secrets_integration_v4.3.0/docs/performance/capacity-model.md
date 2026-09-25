# Capacity model

| ID | INV55-PERF-CAPACITY | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Measured (single host)

Source: `evidence/benchmark_baseline.json` (`tools/benchmark.py`, run 2026-09-23T07:02:17Z). Host: this sandbox, CPython 3.11.15, x86_64 Linux, 2 CPUs. In-process `InMemoryProvider`; each op = resolve + use round trip including HS256 verification; n = 3000 per scenario. **Single-host numbers, not fleet measurements**; they exclude network, Vault and fsync (`FileAuditSink`) latency.

| Scenario | ok / n | shed | p50 | p95 | p99 | p99.9 | max | throughput |
|---|---|---|---|---|---|---|---|---|
| steady (1 thread) | 3000/3000 | 0 % | 0.21 ms | 0.33 ms | 0.50 ms | 1.42 ms | 1.91 ms | 4 330 ops/s |
| cold | 3000/3000 | 0 % | 0.21 ms | 0.31 ms | 0.42 ms | 1.41 ms | 2.31 ms | 4 327 ops/s |
| burst (16 threads) | 3000/3000 | 0 % | 8.06 ms | 15.5 ms | 21.4 ms | 53.1 ms | 54.0 ms | 1 834 ops/s |
| overload (`max_in_flight`=8, 32 threads) | 808/3000 | 73 % | 6.42 ms | 13.7 ms | 26.1 ms | 43.5 ms | 43.5 ms | 3 455 ops/s (admitted) |
| per-tenant (64 tenants) | 3000/3000 | 0 % | 0.20 ms | 0.33 ms | 0.43 ms | 1.93 ms | 31.3 ms | 4 221 ops/s (0.99× steady p50) |

Findings:
- One process delivers ~4.3k resolve+use ops/s on one thread. Under 16-way in-process concurrency, throughput **drops** to ~1.8k ops/s and p99 rises to ~21 ms, because of the CPython GIL switch interval and contention on `SecretsService._lock` (RLock). Adding threads does not add capacity.
- **Scaling rule:** scale by process-per-core (and horizontally by instance), not by threads. Keep per-process concurrency low; size `max_in_flight` accordingly. Open finding WVR-030.
- Overload shedding works: with `max_in_flight`=8 and 32 threads, 73 % of requests were shed OVERLOADED (the coordinator's runs saw ~73–80 %). Admitted requests stayed below 27 ms p99.
- Per-tenant overhead: 64 tenants ran at 0.99× steady p50. A defect found by this benchmark (`PolicyEngine` recomputing the digest and scanning all rules each decision, 2.73× overhead) was fixed by caching the digest and a per-tenant rule index (`identity.py::PolicyEngine.replace`).

## Limits-derived model (per process)
- Concurrency ceiling `max_in_flight` = 256; per tenant 200/s (burst 400); per workload 50/s (burst 100).
- Leases <= 100 000; values shared with cache (<= 64 KiB each).
- Provider load ≈ instances × hot distinct secrets / `cache_ttl_s` (30 s) + misses.
- Audit: one fsync per audited event, serialized by `FileAuditSink._lock`; not included in the benchmark and expected to dominate with a file sink.

Saturation signals: `health()["in_flight"]`; `inv55_requests_total{outcome="retryable"}`; `leases_active`; `Metrics.dropped_series`; `inv55_request_seconds` p99. Not measured: Vault-backed path, fsync, multi-process, fleet, soak (WVR-005).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Real single-host benchmark numbers; process-per-core rule |
