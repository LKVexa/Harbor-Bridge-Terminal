# Performance analysis, capacity model and resource bounds (C061–C070)

Baseline: `benchmarks/results/baseline-linux-x86_64-cpython3.11.json` (2-vCPU shared CI container,
CPython 3.11.15, Node v22.22.2). These are regression baselines, **not** capacity claims for production
hardware. Thresholds: `benchmarks/thresholds.json` (status **PROPOSED**). Gate: `tools/perf_gate.py`.

## Measured baseline (p50 unless stated)

| Metric | Value |
|---|---|
| verify, small (8 functions) | ≈ 0.4 ms (p99 ≈ 0.8–1 ms) |
| verify, medium (1 000 functions) | ≈ 47 ms |
| verify, large (10 000 functions, 70 000 instructions) | ≈ 585 ms; peak heap ≈ 34 MiB |
| rewrite size overhead (dynamic addresses) | ≈ +60–80 % bytes for access-dense code |
| verify throughput (small, one core) | see `verification.throughput_small_verifications_per_s` |
| **runtime overhead, load-bound worst case (V8)** | **≈ +33 – 38 %** (3 runs) |
| runtime overhead, compute-mixed (≈ 12 ops per load) | ≈ 0 % (± 1 %) |
| soak, 20 s submit+load cycles | ≈ 2 100 cycles, heap growth ≈ 2.8 MiB in second half (replay cache holding unexpired nonces — bounded), audit chain INTACT, 0 leaked instances |

## Contract SLO status

The contract promises "masking overhead at or below 15 %". The perf gate evaluates it on two workloads:
**PERF-01 (load-bound) FAILS at ≈ 36 %**; PERF-02 (compute-mixed) passes. This is recorded as residual risk
R-01 and waiver candidate W-01; it is not hidden. Reason: V8 keeps its own bounds checks, so masking is
pure additional work (`const; and; const; add` per access). Paths to close it: (a) engines that elide
bounds checks when partitions are guard-backed, (b) hoisting the mask out of loops with a verifier that
can prove loop-invariant confinement (new ADR), (c) re-scoping the SLO to a representative workload mix.

## Avoidable work identified (C065) and optimisations applied (C066)

| Finding | Action | Effect / proof |
|---|---|---|
| Statically known addresses were masked at runtime | Rewriter folds them to a confined constant; verifier re-proves `base ≤ E ≤ base+mask` | One instruction instead of four for constant addresses; `ConstantFoldTest`, V8 escape fuzz with 30 % constant addresses |
| Loader re-verification on every load | Verify cache keyed by (artifact digest, profile digest), cleared on config change | Repeat loads skip the O(n) verify; cache cannot outlive a policy change |
| br_table validation copied the operand stack per target (quadratic) | Peek-based check (label arity ≤ 1) | Regression test `test_br_table_with_deep_stack_is_linear` |
| Engine job serialisation (base64 over stdin) | Kept: process isolation per job is a security property (INV-39); cost measured (~40–60 ms process start) and documented | batching many calls per job is the supported optimisation |
| Custom sections copied into rewritten output | Non-`name` custom sections stripped (their offsets go stale) | smaller artifacts, no stale DWARF |

No optimisation changes artifact binding, determinism, isolation or failure semantics (S-PREC-01).

## Resource bounds (C067)

All growth is bounded: see `INTERFACES.md#limits` (inputs), admission caps (concurrency/queue), replay cache
(fails closed when full), audit spool (fails closed when full), metrics series cap, log/explain ring
buffers, engine heap cap (`--max-old-space-size=256`) and one process per job.

## Capacity model and saturation signals (C069)

Verification cost is linear: `t_verify ≈ 8.4 µs × instructions` on the baseline host (70 000 instructions ≈
585 ms). With `admission.max_concurrent = C` workers, sustainable verify throughput ≈
`C × cores_available / t_verify`. Saturation signals, in the order they fire:

1. `sfi_submit_latency_ms` p95 rising above 2× baseline;
2. admission `waiting > 0` sustained (queue forming);
3. `sfi_modules_loaded_total{outcome="rejected",code="SFI_OVERLOADED"}` rate > 0 (shedding);
4. `SFI_DEADLINE_EXCEEDED` rate > 0 (work exceeding the deadline).

Alerts for 2–4 are in `ops/alerts/inv45-rules.yml`. Scale out when (2) persists > 5 min.

## Power and thermal (C068)

**Not measured.** The CI container exposes no RAPL/thermal sensors and no constrained edge hardware was
available. Far-edge deployment is declared unsupported (S-FUN-05) until an edge measurement exists.
Open external item; owner UNASSIGNED.

## Fleet scale (C088)

Single-host only. Soak (20 s) and burst (1 000 requests, 32 threads) run in CI; fleet-scale certification
needs a real fleet and is an open external item.
