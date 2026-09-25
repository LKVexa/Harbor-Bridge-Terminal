# INV-18 performance specification (C061–C070, C088)

Reference environment for every number below: Linux x86-64 container, CPython 3.11.15,
`bench.run(quick=True, reps=5)` on 2026-09-23 (`conformance/BENCH_BASELINE.json`, which also
records full platform metadata). Numbers are **measured**; thresholds are **PROPOSED**
(W-C062) until the approving authority signs `conformance/PERFORMANCE_THRESHOLDS.json`.

## Methodology (C061)

`bench.py`: 200-iteration warm-up; GC disabled only while sampling; `perf_counter_ns`
around each single operation; 3 000 samples × 5 repetitions (quick) or 50 000 × 5 (full);
variance reported as the standard deviation of p50 across runs; memory via `tracemalloc`;
import time via a fresh interpreter subprocess; raw results stored as JSON. Storage and
network overhead: N/A (the core does no I/O — verified by AuthorityTest). Power: N/A pending
approval (W-C068).

## Measured baseline (C061, C062)

| Operation (bare `Future`) | p50 | p95 | p99 (median of runs) | max |
|---|---|---|---|---|
| create | 2.3 µs | 2.3 µs | 3.8 µs | 33 µs |
| resolve | 1.1 µs | 1.2 µs | 2.7 µs | 25 µs |
| resolve_error | 1.1 µs | 1.1 µs | 2.5 µs | 29 µs |
| abandon | 1.0 µs | 1.0 µs | 2.2 µs | 32 µs |
| take | 0.8 µs | 0.9 µs | 1.7 µs | 22 µs |

Governed cycle (create→resolve→take through `Runtime`): p50 30–55 µs (varies with host
noise), p99 ≈ 130 µs. Bare throughput ≈ 237 000 cycles/s. Import ≈ 26 ms. Memory: 1.2 KB per
bare future, 2.9 KB per governed future; after release ≈ 0.7 KB per future remains while the
bounded tombstone ring (16 384 entries ≈ 10 MB max) holds released ids — bounded, not a leak
(soak second-half growth: 1.6 KB). Contention (16 resolvers): p99 ≈ 49 µs, zero invariant errors.

**Source SLO "p99 resolution under 1 µs" is not met** by CPython (bare resolve p99 ≈ 2.7 µs).
Proposed thresholds: bare p50 ≤ 2 µs, p95 ≤ 4 µs, p99 ≤ 8 µs, max ≤ 1 ms; governed
p50 ≤ 120 µs, p99 ≤ 800 µs; throughput ≥ 100 000/s; memory ≤ 2 KB bare / 4.5 KB governed;
import ≤ 100 ms. Sample size: 15 000 samples per operation per run set (p99 resolved to
±0.1 µs across repetitions).

## Load regimes (C063)

| Regime | Result |
|---|---|
| steady (2 000 cycles) | p99 ≈ 85 µs, correctness intact |
| short burst (1 000 outstanding) | all admitted, drained, outstanding 0 |
| sustained burst (5 × 1 500) | all admitted, drained |
| overload (5 000 requested vs 2 000 limit) | 2 000 admitted, 3 000 rejected `RESOURCE_EXHAUSTED`, memory bounded |
| post-overload recovery | p99 ≈ 95 µs — back to steady state |
| increasing concurrency 1/2/4/8/16 threads | 16k → 6k → 6k → 5k → 6k cycles/s aggregate — **lock convoy (DEBT-PERF-01)** |
| scale-out / scale-in | N/A: process-local; scale by processes |

Every regime also checks outstanding = 0 and zero double resolutions/takes.

## Per-workload overhead (C064)

Unit: bytes and µs per outstanding future. Scaling 1 → 10 000 outstanding: peak bytes per
future 7.6 KB (fixed overhead dominates at n=1) → 3.0 KB (flat from 100 upward); time per
op flat (60–80 µs per 3 ops). No superlinear growth. Per-tenant bookkeeping: one dict entry
per tenant with live futures.

## Copies, hops, synchronisation (C065) and optimisations (C066)

Profile of one governed cycle: payload copies **0** (identity preserved), network hops 0,
serialisation in core none, lock acquisitions: 3 on the future's condition, 3 on the registry.
Unavoidable synchronisation: the per-future lock (at-most-once) and the registry lock
(admission accounting). Largest allocation source: telemetry (≈ 35 % of cycle cost).

| Optimisation | Decision | Evidence |
|---|---|---|
| OPT-1 single `os.urandom` for all random fields (was 7 `secrets.token_hex` calls) | **adopted** | governed cycle p50 37 µs → 30 µs on the same host |
| zero-copy payload hand-off | already the case | `profile_ops.payload_identity_preserved` |
| direct in-process composition | already the case | no hops |
| batching resolutions | rejected | would let one caller resolve many futures atomically — changes semantics |
| caching | only immutable config snapshots (`ConfigStore.values`) | — |
| lock-free / sharded registry | deferred (DEBT-PERF-01) | must keep at-most-once proofs |
| async-native adapter | not required by any adjacent contract | — |
| removing weakref finaliser | rejected | measured no contention gain; loses writer-drop detection |
Any optimisation that weakens at-most-once or single-receiver is forbidden (policy INV18-PREC/1).

## Power / thermal (C068)

Decision: N/A for the core pending approval (W-C068) — no timers, threads or I/O of its
own, so idle overhead is structurally zero; burst power on far-edge hardware unmeasured.

## Capacity model (C069)

`bench.capacity_model(result)`: memory = outstanding × 2.9 KB (+ ≤ 10 MB tombstones) —
tests/test_perf.py::CapacityTest predicts 20 000 futures within 25 %; CPU ≈ 37 µs per
governed cycle; throughput per Runtime ≈ 16–24 k cycles/s on 1 thread; contention knee at
4 threads. Saturation signals: soft limit (warning), hard limit (critical), memory > 50 % of
node, governed p99 > 800 µs, more than 3 threads per Runtime. Safe envelope: ≤ 3 threads
per Runtime (or one Runtime per worker); outstanding ≤ soft limit; ~290 MB at the default
hard limit.

## Regression gate (C070)

`bench.compare(result, baseline, waivers)` gates p50/p95/p99 resolve, take, create, governed
cycle, throughput, memory and import time against `BENCH_BASELINE.json` with per-metric
allowed ratios **and** an absolute noise floor (1 µs for bare-operation percentiles, 20 µs for
the governed cycle and import time — shared-host timer jitter measured at ~1 µs on p95); an approved waiver (WAIVERS.json) is the only override.
tests/test_perf.py::RegressionGateTest injects a 3× regression and proves it is blocked;
`certify.py` runs the comparison on every gate execution.
