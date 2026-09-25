# INV-68 benchmarks, efficiency and bounds 4.3.0 (MC-22, MC-23, MC-24, MC-31)

Numbers below are from `evidence/PERF.json` of the release run (CPython 3.11,
Linux x86_64 container, shared CPU; see `machine` in the file). Re-run:
`python -m inv68_resource_packing.tools.bench`. Baseline envelope:
`bench/PERF_BASELINE.json` (regression gate: p95 > baseline × 1.5 **and** > 0.5 ms
absolute, or any change in hosts used).

## The 4.2.0 performance defect (found by this pass)

| Profile | 4.2.0 | 4.3.0 | Contract |
|---|---|---|---|
| steady-1000 (1000 mixed workloads) | p50 **311 ms**, max 521 ms | p50 ≈ 6 ms, p99 ≈ 8–9 ms | p99 < 100 ms |
| worst-5000 (every workload needs its own host) | **51 s** | p50 ≈ 45 ms | — |

Cause: `Host.fits` / `Host.place` re-validated the workload for every candidate
host, and full hosts stayed in the first-fit scan forever — O(n·h) validations.
Fix: validate once; close a host when it cannot fit the smallest *remaining*
request in some dimension. A closed host could never accept a later workload, so
every decision is unchanged — proven by `test_MC22_differential_against_420_reference`
(300 random batches) and the fuzz reference oracle (3000 cases).
Record: `bench/PERF_4.2.0_COMPARISON.json`.

## Profiles (4.3.0)

| Profile | Workloads | Purpose |
|---|---|---|
| tiny-1 | 1 | fixed overhead |
| steady-1000 | 1000 mixed | contract SLO |
| burst-5000 | 5000 mixed | burst batch |
| fleet-20000 | 20000 small | fleet cardinality |
| worst-5000 | 5000 × one-per-host | complexity attack (T7) |
| service-1000 | 1000 via PackingService | boundary overhead: auth, validation, audit fsync, explain |

Method: 3 warm-up runs, 40 timed runs (10 for > 5000 workloads), `perf_counter`,
linear-interpolated percentiles, `tracemalloc` peak per call, fixed seeds, machine
metadata recorded. Per-tenant overhead: the service profile is single-tenant; the
per-tenant quota/rate bookkeeping is O(1) per request.

## Efficiency (SLO)

200 random batches (seed 68, 20–400 workloads): hosts within 10 % of the placeable
volume lower bound in 99.5 % of batches (SLO ≥ 95 %), mean ratio ≈ 1.008, worst 1.11.
Small-input quality against the exact optimum (brute force, ≤ 7 workloads, 150
cases): FFD never exceeded 1.5·OPT + 1 (`test_MC30_quality_against_exact_optimum_on_small_inputs`).

## Hot-path analysis and N/A rationale (MC-23)

| Candidate optimisation | Assessment |
|---|---|
| repeated validation in the first-fit scan | **fixed** (dominant cost in 4.2.0) |
| full hosts in the scan | **fixed** (closed-host pruning) |
| sort | O(n log n), < 10 % of steady-1000 time — no action |
| copies / serialisation | engine copies each workload once (non-mutation guarantee); `to_dict` only at the boundary — no action |
| context switches / hops | none in the engine (single call, no I/O); service adds one fsync per audit record — the dominant service cost, required for durability |
| index structure for first fit (segment tree) | not needed at declared scale: worst-5000 45 ms; revisit above 50 000 workloads |

## Hard bounds (MC-23 D)

payload ≤ 4 MiB, workloads ≤ 10 000 per request (config), in-flight ≤ 8, queue ≤ 32,
no fan-out (one optional capacity-source call per request), memory ≈ 470 KB peak
for steady-1000 and ≈ 8 MB for fleet-20000 (tracemalloc).

## Not measured (open)

Edge power/thermal (needs constrained hardware — MC-23 E, DEBT-003); production
saturation model from live telemetry (MC-24 E); certification-length soak ≥ 1 h
(the release run soaked 60 s — MC-31).
