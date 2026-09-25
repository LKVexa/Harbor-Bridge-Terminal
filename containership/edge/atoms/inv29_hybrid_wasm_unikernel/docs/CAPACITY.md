# Performance baseline, thresholds and capacity model (INV29-MC069 – MC075, MC077, MC078)

Measured by `python tools/bench.py` (raw data: `perf/baseline.json`; latest run: `perf/latest.json`).
**Hardware class of the committed baseline:** CI-class Linux x86_64 container, CPython 3.11. These numbers are a *reference*, not production evidence — the production baseline must be re-captured on the target node class (MC069 stays IMPLEMENTED_LOCAL until then).

## Baseline latency (ms, n = 2000)

| Operation | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|
| `verify()` | 0.0023 | 0.0027 | 0.0061 | 0.034 |
| `compose()` | 0.0032 | 0.0041 | 0.0089 | 0.025 |
| `Admitter.admit()` (full pipeline, 2 HMAC verifies + sign + schema) | 0.138 | 0.200 | 0.236 | 0.389 |
| `records.parse(..., schema=)` | 0.135 | 0.229 | 0.253 | 0.306 |
| `verify_record()` | 0.085 | 0.126 | 0.151 | 0.207 |

## Proposed thresholds (MC070) — owner to ratify in `governance/SLO.md`

| Operation | p50 | p95 | p99 | worst-case |
|---|---:|---:|---:|---:|
| admit | ≤ 1 ms | ≤ 5 ms | ≤ 10 ms | ≤ 25 ms (alert `INV29AdmissionLatencyP99`) |
| verify_record (PLN-04 side) | ≤ 0.5 ms | ≤ 2 ms | ≤ 5 ms | ≤ 10 ms |

## Load and overload (MC071)
Admission throughput by worker threads: 1 → ~5.3k/s, 4 → ~5.8k/s, 16 → ~4.5k/s. Admission is CPU-bound pure Python under the GIL; adding threads does **not** add capacity and past ~4 threads contention reduces it. Scale **out** by process/replica, not threads. Overload behaviour: requests queue in the caller; nothing is dropped silently, and saturation of the replay cache refuses (fail closed) with alert `INV29ReplayCacheSaturated`.

## Per-workload overhead (MC072)
One admission retains ≈117 B (the replay-cache entry, released after TTL). A composition record is ≈1.5 KB serialized. Per-tenant overhead is zero beyond its records; there is no per-tenant state.

## Copy / serialization analysis (MC073)
Capability scaling (compose p50 / record size): 1 cap 0.003 ms / 678 B · 64 caps 0.014 ms / 1 KB · 512 caps 0.13 ms / 4 KB · 4096 caps 1.6 ms / 32 KB. Cost is dominated by `sorted()` of the import set and canonical JSON. Schema validation is the largest single cost in `admit` (~40 %); it is kept on the hot path deliberately (fail-closed output validation). No network hops or context switches exist inside INV-29; the dependency adapters add one thread hand-off per upstream call.

## Optimization evidence (MC074)
4.3.0 keeps the hot path allocation-light (frozen dataclasses with slots in the model, no deep copies, canonical JSON once for signing). The one measured optimisation opportunity — caching compiled schemas — is already done (`records._SCHEMA_CACHE`). Further work needs production profiles.

## Operational limits (MC075)
Names ≤ 256 chars · capabilities ≤ 4096 × 256 chars · imports per workload ≤ policy (default 64) · record ≤ 1 MiB · nesting ≤ 32 · attestations ≤ 8 · replay cache 100 000 entries per process (default) · metric series ≤ 200 per metric · decision ring 10 000 events · dependency pool 8 threads.

## Capacity model (MC077)
`replicas = ceil(peak_admissions_per_s / (0.6 × per_replica_throughput))`, with per-replica throughput measured on the target node class (≈5k/s reference). Replay-cache sizing: `capacity ≥ peak_admissions_per_s × record_ttl_s × 1.5`. Saturation signals: `inv29_replay_cache_fill_ratio > 0.9`, admission p99 above threshold, dependency breaker open.

## Regression gate (MC078)
`python tools/bench.py` fails (exit 1, `perf/regression_gate.json`) when any p95 regresses by more than 50 % against `perf/baseline.json`. CI runs it on every change; the baseline is only rewritten deliberately with `--write-baseline` on the reference hardware.

## Power / thermal (MC076, P2)
Not measurable in this environment — BLOCKED_EXTERNAL; required only if the far-edge deployment context is selected.
