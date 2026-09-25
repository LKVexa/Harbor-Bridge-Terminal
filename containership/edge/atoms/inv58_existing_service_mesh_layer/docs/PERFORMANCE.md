# INV-58 Performance, bounds and capacity (v4.3.0)

Harness: `tools/bench.py` (stdlib only). Baseline: `perf/baseline.json`, recorded 2026-09-23T07:02:42Z (best of 2) on
CPython 3.11.15 / Linux x86_64 / 2 CPUs (cloud sandbox — a
reference point, not production hardware). Re-baselining is a reviewed change.

## Baselines

| Profile | p50 µs | p95 µs | p99 µs | worst µs | ops/s |
|---|---|---|---|---|---|
| burst.svc.reconcile.8threads | 81.6 | 3129.4 | 10422.0 | 29325.8 | 1,772 |
| mesh.map_identity | 6.7 | 8.6 | 17.0 | 72.9 | 139,511 |
| mesh.reconcile | 2.0 | 2.3 | 3.4 | 161.0 | 484,247 |
| svc.map_identity | 34.3 | 53.5 | 68.1 | 147.4 | 27,007 |
| svc.migrate_route | 150.1 | 206.2 | 286.1 | 6953.2 | 6,355 |
| svc.reconcile | 38.2 | 56.7 | 72.0 | 682.1 | 24,510 |
| svc.report_flow | 68.4 | 95.6 | 120.2 | 645.1 | 16,706 |

Startup (empty → ready): 0.73 ms. Memory: 10 000 routes peak 3664 KiB.
Per-tenant overhead: p50 ratio 200 tenants vs 1 = 0.91 (was ≈1.3 before OPT-2).

## Thresholds

`tools/bench.py::GATE` holds, per metric, an absolute ceiling (p99 identity mapping 100 µs is the
contract SLO) and an allowed regression versus baseline (with a noise floor). `tools/release_gate.py`
fails the release when any metric exceeds `min(ceiling, max(baseline×(1+allowed), baseline+floor))`.

## Load profiles
- **Steady:** single-thread closed loop, 20 000 ops (library) / 5 000 ops (boundary service).
- **Burst:** 8 threads closed loop on the boundary service.
- **Overload:** `test_fault_injection.BurstSoakFleetTest.test_burst_overload_sheds_and_recovers` — saturation → `E_OVERLOADED`, then recovery with in-flight back to 0.
- **Scale-out / scale-in:** BLOCKED — needs a multi-instance deployment (C063 partial).
- **Recovery:** dependency flap tests assert zero extra failed requests after recovery.

## Optimization analysis
| Id | Finding | Decision |
|---|---|---|
| OPT-1 | `RoutePolicyRegistry.migrate_route` copies the whole dict per write (O(n)); p99 migrate is the slowest boundary op. | **Kept.** Copy-on-write is a hardened 4.2.0 invariant the checklist says to preserve. Tracked as TD-01. |
| OPT-2 | Each decision record deep-copied the whole active config (`config.active()`), so per-request cost grew with tenant count (measured p50 ratio 200-vs-1 tenants ≈1.3). | **Applied** in 4.3.0: `ConfigStore.provenance()` returns the immutable provenance without copying. |
| OPT-3 | No network hop is added: INV-58 is in-process policy; the mesh data plane is unchanged. | No action. |
| OPT-4 | Serialization only at audit sink/log sink (JSON). | Kept — audit integrity needs canonical JSON. |
| OPT-5 | Kernel-bypass / zero-copy | Not applicable: no packet path is owned (non-goal "Running the mesh"). |

## Bounds
Every queue/buffer/registry/cache has a ceiling (see `docs/INTERFACES.md#limits`); saturation behaviour: shed (`E_OVERLOADED`), refuse (`E_CAPACITY`), or drop-oldest with anchor (audit ring, bypass evidence, logs) — never unbounded growth. The soak test asserts the ceilings hold.

## Capacity model
Saturation signals: `inv58_saturation_ratio` (in-flight / max), `inv58_admission_shed_total`,
`inv58_route_registry_size` vs `max_routes_per_tenant`, `inv58_bypass_backlog` vs `max_flags`.
Rule: provision so peak `inv58_saturation_ratio` stays < 0.7; at the measured boundary p50 of
~38 µs one instance sustains ≈24,510 reconcile ops/s single-threaded; required
instances ≈ peak_ops / (0.7 × measured ops/s). Route memory ≈ 375 B per route.

## Power
BLOCKED (INV-58-C068): no constrained edge hardware or power telemetry is available. Nothing is estimated.
