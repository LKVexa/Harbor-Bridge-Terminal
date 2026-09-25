# INV-37 performance, capacity and efficiency

**Version:** 4.3.0 · Covers INV-37-C061–C070, C088. Harness: `benchmarks/bench.py` (reproducible: `python benchmarks/bench.py --out FILE`); gate: `tools/perf_gate.py` against `PERF_THRESHOLDS.json` and `artifacts/benchmarks/baseline.json`.

## Baseline (audit sandbox — not a production baseline)

Host: Linux x86_64, CPython 3.11.15, sandbox VM; object 64 MiB, chunk 1 MiB; each path run 5× and per-field medians reported (single-run p99 on a shared host tripped the gate once at 2.0× — hence repeats).

| Path | Throughput | p50 / p99 per chunk | Peak alloc ÷ object | Data-plane copies |
|---|---|---|---|---|
| Legacy in-memory receiver (v4.2 behaviour) | ≈148 MiB/s | 3.3 / 3.8 ms | **2.0×** | 2 per object |
| Shared-memory zero-copy receiver | ≈198 MiB/s | 2.5 / 2.7 ms | **0.0003×** | **0** (1 ingress copy by producer) |
| Durable checkpoint, fsync, 64 KiB chunks | ≈32 MiB/s (storage-bound) | 1.8 / 3.5 ms | — | 1 (to storage, required) |

Also recorded: import/startup time, manifest hashing rate, restart recovery time, CPU user/sys, peak RSS, steady admission latency, burst (64 offered vs capacity 8 → rejections, no cascade), overload rejection ratio, recovery to 0 active, scale-out (1→8 workers, hashing-bound, saturates at CPU count), per-tenant service overhead. Exact values: `artifacts/benchmarks/baseline.json`.

**Power/thermal (C068): not measured** — no RAPL/thermal sensors in the sandbox; the edge profile halves concurrency and mapped memory as a proxy. Gate criterion `power_thermal_edge` stays BLOCKED until measured on target edge hardware.

## Optimisations applied (C066)

Zero-copy shared memory (in-place hashing, read-only object view); `memoryview` slicing for manifest construction; `pwrite` directly at chunk offset for durable path (no assembly buffer); duplicate chunks short-circuit before storage. Not applied: batching of fsyncs (would weaken RPO), kernel bypass (INV-38), host/guest sharing (ADR-0001 phase 2).

## Thresholds and regression gate (C062, C070)

`PERF_THRESHOLDS.json` holds absolute invariants (0 copies on shm; peak alloc ≤1 %; recovery after burst; startup ≤0.5 s) and baseline-relative limits (throughput ≥70 %, p99 ≤150 %, fsync p99 ≤200 %). Missing metrics → BLOCKED, regressions → exit 1. Thresholds are **proposed** until the architecture approver signs them.

## Capacity model and saturation signals (C069)

- Memory: `peak ≈ Σ active (object_size × k)` where k = 2 for legacy copy receiver, ~0 for shm (region counted once as mapped memory), 0 for durable path (data on disk). Preflight enforces `max_concurrent_transfers × max_object_bytes ≤ host_memory_budget` and `max_mapped_bytes ≤ host_memory_budget`.
- CPU: hashing-bound; ≈ `hash_rate_per_core × min(cores, active)`; sandbox ≈ 390 MiB/s per core.
- Storage: `checkpoint.max_bytes ≥ Σ in-flight object sizes + quarantine retention`.
- Saturation signals: `admission.metrics().saturation` (max of slot and byte utilisation), `pending`, `throttle_reasons`, `transfers_stalled`, `chunk_accept_seconds` p99 growth, `admission_rejected_total{reason}`. Scale out when saturation > 0.8 for 15 min or p99 exceeds threshold.

## Not yet measured (gate criterion `soak_burst_fleet_scale`)

Multi-hour soak, fleet-scale (many nodes), long-tail latency on production hardware, per-workload overhead inside real embedding services.
