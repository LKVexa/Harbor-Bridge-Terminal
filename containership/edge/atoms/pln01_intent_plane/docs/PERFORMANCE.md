# Performance baselines and efficiency analysis (MC-031, MC-032)

Evidence: `conformance/benchmark_results.json` (build sandbox: Linux x86_64, 2 vCPU, CPython 3.11) and the gate
verdict `conformance/perf_gate_result.json`. Thresholds: `conformance/perf_baseline.json` (**provisional**, not yet
approved; production reference hardware and power measurement are open — waiver W-005).

| Scenario | Result (sandbox) | Threshold |
|---|---|---|
| 10k-node chain plan (max of 5) | ≈ 0.04–0.08 s | SLO ≤ 2 s |
| 10k-node fan-out plan | ≈ 0.04 s | +50 % regression |
| Service declare p99, in-memory | ≈ 0.26 ms | +100 % |
| Service declare p99, durable (fsync off in bench) | ≈ 0.7 ms | +100 % |
| Burst, 16 threads | ≈ 3 800 req/s | ≥ 50 % of baseline |
| Memory | ≈ 909 B/node | +25 % |

## Optimisation found and fixed during this overhaul
The first v4.3.0 service path computed tenant quota usage by snapshotting (deep-copying) the whole graph on every
request — O(N) per request, O(N²) per load. Measured: 2 000 declarations p50 4.96 ms, 188 req/s. Replaced by an
incrementally maintained per-tenant counter updated inside `_commit` (and reverted on WAL failure, recomputed on
restore). Result: p50 0.14 ms, 6 680 req/s — **≈ 36× throughput**, and flat with graph size. Correctness guarded by the
soak test (counter equals recount after churn, restore and rollback).

## Algorithmic analysis
declare O(d + depth-of-cycle-check); retract O(V + E) (reverse index built per call — acceptable, retract is rare);
plan O(V + E log V) heap-based Kahn; diff/rollback O(Δ·h) over retained deltas; audit O(1) append.
