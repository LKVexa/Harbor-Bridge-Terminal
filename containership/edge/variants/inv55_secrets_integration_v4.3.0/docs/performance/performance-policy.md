# Performance policy

| ID | INV55-PERF-POLICY | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Baseline

Source: `evidence/benchmark_baseline.json` (`tools/benchmark.py`, run 2026-09-23T07:02:17Z). Host: this sandbox, CPython 3.11.15, x86_64 Linux, 2 CPUs. In-process `InMemoryProvider`; each op = resolve + use round trip including HS256 verification; n = 3000 per scenario. **Single-host numbers, not fleet measurements**; they exclude network, Vault and fsync (`FileAuditSink`) latency.

| Scenario | ok / n | shed | p50 | p95 | p99 | p99.9 | max | throughput |
|---|---|---|---|---|---|---|---|---|
| steady (1 thread) | 3000/3000 | 0 % | 0.21 ms | 0.33 ms | 0.50 ms | 1.42 ms | 1.91 ms | 4 330 ops/s |
| cold | 3000/3000 | 0 % | 0.21 ms | 0.31 ms | 0.42 ms | 1.41 ms | 2.31 ms | 4 327 ops/s |
| burst (16 threads) | 3000/3000 | 0 % | 8.06 ms | 15.5 ms | 21.4 ms | 53.1 ms | 54.0 ms | 1 834 ops/s |
| overload (`max_in_flight`=8, 32 threads) | 808/3000 | 73 % | 6.42 ms | 13.7 ms | 26.1 ms | 43.5 ms | 43.5 ms | 3 455 ops/s (admitted) |
| per-tenant (64 tenants) | 3000/3000 | 0 % | 0.20 ms | 0.33 ms | 0.43 ms | 1.93 ms | 31.3 ms | 4 221 ops/s (0.99× steady p50) |

## Thresholds (#62)
| Path | p50 | p99 | max | Status vs baseline |
|---|---|---|---|---|
| resolve+use, in-process, sequential | 1 ms | 5 ms (contract SLO) | 50 ms | MET (0.21 / 0.50 / 1.91 ms) |
| resolve+use, 16-way in-process concurrency | 1 ms | 5 ms | 50 ms | **NOT MET** (8.06 / 21.4 / 54.0 ms) — WVR-030 |
| admitted requests under overload | — | 50 ms | 100 ms | MET (26.1 / 43.5 ms) |
| resolve via Vault | 20 ms | 250 ms | 2 s (`request_timeout_s`) | NOT MEASURED |
| rotate | 30 ms | 300 ms | 2 s | NOT MEASURED |

The contract SLO "p99 under 5 ms from cache" (`contract.py`) holds for sequential calls only. Deployments MUST scale process-per-core and keep per-process concurrency low until WVR-030 is resolved.

## Cache policy (#66)
- Positive cache per (tenant, name), TTL `cache_ttl_s` = 30 s; invalidated locally on `rotate` and `retire`.
- No negative caching. Stale serving only with `stale_grace_s > 0`.
- Policy decisions: `PolicyEngine` caches its digest and a per-tenant rule index, rebuilt only in `replace()`; no decision cache (policy changes apply on the next call).
- Batching, connection reuse: NOT IMPLEMENTED.

## Regression gate (#70)
- `tools/benchmark.py` writes and compares against `evidence/benchmark_baseline.json`.
- A release MUST fail if a tracked p50/p99 regresses by > 10 % versus the baseline on the same host class. Baseline updates MUST record host, Python version and source revision.
- The baseline comes from one sandbox host; cross-host comparison is not valid.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Real baseline; concurrency finding |
