# Performance, efficiency and capacity — `DOC-INV52-PERF` v4.3.0 (C061-C070)

Harness: `bench.py` (reproducible; `--quick` for CI). Reference run: `evidence/perf.json` (full run, 20,000 publishes per series) on CPython 3.11.15, Linux x86_64, 2 vCPU cloud container. **One host, not a representative platform** — numbers are a baseline for regression detection, not capacity certification.

## Baselines (C061, C062)

| Series | p50 | p95 | p99 | worst |
|---|---|---|---|---|
| publish, 1 route | 62 µs | 130 µs | 185 µs | 1.8 ms |
| direct deliver (deepcopy + append) | 11 µs | 18 µs | 46 µs | 1.2 ms |
| **overhead p99** (publish − direct) | | | **138 µs** (SLO ≤ 1 ms: met) | |
| startup (`bootstrap`) | 0.19 ms | | 3.3 ms | |

Proposed thresholds (`perf/baseline.json`, PROPOSED): p50 ≤ 250 µs, p95 ≤ 500 µs, p99 ≤ 1 ms, worst ≤ 20 ms, ≥ 2,000 msg/s steady, startup p99 ≤ 50 ms.

**4.2.0 → 4.3.0 cost, measured in the same process (3 runs):** p50 37 µs → 62–63 µs; p99 93–125 µs → 168–185 µs. The +25 µs buys the decision record, size and depth bounds, trace validation and the latency histogram. Profiling shows three `deepcopy` calls (unchanged from 4.2.0) are still ~60 % of the cost.

## Load profile (C063, C088)

| Scenario | Result |
|---|---|
| steady, single thread | 14,530 msg/s |
| burst, 8 threads | 4,710 msg/s (GIL + lock contention; correct counts) |
| overload (1,000/s quota, burst 200, unthrottled offer) | 94 % shed with retryable `PK_MSG_OVERLOADED`; accepted p99 1.14 ms (above the 1 ms p99 target while overloaded — recorded, not hidden) |
| scale-out routes 1 → 8 → 64 | p50 61 → 147 → 849 µs (linear in fan-out) |
| scale-in 64 → 1 (unsubscribe) | p50 67 µs (returns to the 1-route baseline) |
| recovery: 5,000 queued messages replayed after outage | 58 ms, 5,000/5,000 delivered, order kept |
| memory: 3,000-publish rounds after warm-up | round 2 growth 1.3 KB (bounded) |

Soak (hours) and fleet-scale runs: not performed (BLOCKED — need an environment).

## Per-tenant / per-workload overhead (C064)

`TenantBus` (fresh signed token per publish: HMAC verify, replay cache, capability check, namespacing, audit append) adds **~62 µs p50** over the raw bus (124 µs vs 63 µs). One hundred tenants on one bus: p50 63 µs (no measurable effect of topic count).

**Defect found by this measurement:** the first run showed +436 µs p50 per tenant publish. The replay-cache eviction inherited from INV-46's `TokenAuthority` copied the entire nonce cache (`list(self._seen.items())`) on every verify, making verification O(cache). Fixed here; regression test `test_security.py::test_verify_cost_does_not_scale_with_replay_cache`. **INV-46 v4.3.0 still carries the defect.**

## Avoidable copies and optimisation (C065, C066)

| Mode | deep copies per publish (r routes, d deliveries) | p50 at 16 routes |
|---|---|---|
| `predicate_view="copy"` (4.2.0 behaviour, runtime default) | 1 + r + d | 253 µs |
| `predicate_view="frozen"` (config default) | 1 + 1 frozen view + d | 80 µs (−68 %) |

No serialization, context switch or network hop occurs in the in-process path; broker hops belong to Dapr. Batching, zero-copy and kernel bypass are not applicable to an in-process Python library and are declared not applicable rather than claimed.

## Resource bounds (C067)

All bounds in `docs/INTERFACES.md` §Limits; fuzzed invariant `test_publish_random_messages_keeps_invariants`.

## Power / thermal (C068)

NOT_MEASURED — needs an instrumented edge node (waiver W-002).

## Capacity model and saturation signals (C069)

Single-thread capacity ≈ 1 / p50(publish with r routes); from the reference: ~16 k msg/s at r = 1, ~6.8 k at r = 8, ~1.2 k at r = 64 per interpreter. Saturation signals: `shed` rate > 5 % (overload alert), dead-letter fill ≥ 80 %, replay-cache fill (`TokenAuthority.replay_cache_fill`) ≥ 80 %, p99 publish > 1 ms. Scale out (more publisher processes / sites) before any of them trips. The model is a single-host extrapolation and must be re-fitted on fleet data.

## Regression gate (C070)

`gate.py` runs `bench --quick --check perf/baseline.json`; any threshold breach fails the engineering verdict.
