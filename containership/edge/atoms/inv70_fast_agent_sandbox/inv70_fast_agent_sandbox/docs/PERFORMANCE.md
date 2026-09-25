# Performance (C061, C063–C066, C068, C070, C088)

Run it yourself: `python -m inv70_fast_agent_sandbox.tools.bench --out perf/results.json`. Each output records the environment, version and time. The baseline was captured on CPython 3.11.15, Linux x86_64, 2 vCPU (`perf/baseline.json`).

## Baseline highlights (p50)
| Path | p50 |
|---|---|
| VM 6-instruction arithmetic (in-process) | ~11 µs |
| VM validation only | ~2 µs |
| VM 1,000-fuel spin | ~0.48 ms |
| Governed run, process isolation, cold spawn | ~63 ms |
| Governed run, warm single-use worker | ~2.2 ms |
| Burst: 8 callers × 10 with concurrency 4 | 40 ok / 40 shed (FB-C001), recovers |
| Per tenant (A/B/C, same load) | roughly equal; tenant attribution comes from the `tenant` label |

## Overhead analysis (C065)
- **Serialization/copy:** the program and limits are pickled once parent→child. Each host call makes one pickle round trip (argument and result, both bounded by `max_value_bytes`). The result is pickled once.
- **Context switches:** 2 per run, plus 2 per host call (pipe). The host callback runs on a parent-side thread pool.
- **Network hops:** none. The sandbox never opens sockets.
- **State duplication:** none across runs by design, since every worker is single-use. The warm pool only holds idle, never-used interpreters.
- **Dominant cost:** interpreter start-up (`spawn`), which is ~95% of a cold run.

## Optimizations adopted (C066)
- **Warm single-use workers** (`warm_workers`): cold p50 went from 62.7 ms to 2.2 ms. Isolation is unchanged because a worker is used exactly once.
- **Rejected:** reusing a worker for several runs (breaks fresh-instance isolation) and caching compiled modules (not allowed by ADR-0001 until it is keyed by digest).

## Regression gate (C070)
`--gate perf/baseline.json` exits 1 if a VM p50 or the service p50 regresses by more than 25%, if the system does not recover after a burst, or if the baseline is missing or from another machine class. CI runs it on every change.

## Edge power/thermal (C068) — BLOCKED
Procedure: on the edge reference device, measure idle watts, then run 10 minutes of the `arith6` loop at 50% and 100% of `rate_per_s` with an inline power meter, recording SoC temperature every second and noting any throttling. Record the results in `perf/edge_power.json`. No such hardware was available.

## Not yet measured
Soak over 24 h or more, and fleet scale (C063 and C088 remain PARTIAL).
