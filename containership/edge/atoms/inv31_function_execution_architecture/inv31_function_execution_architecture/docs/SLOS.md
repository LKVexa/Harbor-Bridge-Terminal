# INV-31 SLOs and performance thresholds (C013, C062, C070, C091)

**Status: PROPOSED — not approved.** Owner UNASSIGNED; no error-budget policy is in force.

| Signal | Proposed threshold | Measured (this build, see `evidence/bench.json`) |
|---|---|---|
| Tenant isolation | 0 violations | 0 in fuzz + stress |
| Version fidelity | 0 violations | 0 |
| Warm rate, steady state | ≥ 80 % | reported by benchmark |
| Gateway invoke latency p99 (in-process) | ≤ 1 ms | reported by benchmark |
| Raw pool invoke latency p99 | ≤ 200 µs | reported by benchmark |

`tools/bench.py --check` compares a run against `evidence/bench_thresholds.json` and
exits 1 on regression. It is wired into CI as a *report*, not a release block, because
the thresholds are unapproved (C070 stays PARTIAL).
