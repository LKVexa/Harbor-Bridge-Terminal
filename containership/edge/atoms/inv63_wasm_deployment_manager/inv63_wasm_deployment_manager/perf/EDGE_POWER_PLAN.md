# INV-63 Edge Power and Thermal Measurement Plan

| Field | Value |
|---|---|
| Document ID | INV63-PERF-EDGE-POWER |
| INV-63 C-IDs covered | C068 |
| Status | DRAFT — pending approval. **NOT MEASURED** — plan only, not executed |
| Owner | Performance reviewer (role) — UNASSIGNED |
| Reviewers | SRE lead (role), Edge hardware owner (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when target edge hardware changes. |

No power or thermal data exists for INV-63. Evidence key `edge-hardware` is open. No edge hardware was available.

## Hardware classes (to be confirmed by owner)
| Class | Example profile | Meter |
|---|---|---|
| E1 near-edge x86 | 4-core x86_64, 8 GB, SSD | Intel RAPL (package + DRAM) via `powercap` sysfs |
| E2 far-edge ARM | 4-core aarch64 SBC, 2–4 GB, eMMC/SD | INA219 on the DC supply rail (I²C, ≥ 10 Hz) |
| E3 constrained far-edge | 2-core aarch64, 1 GB, flash | INA219 |

## Method
1. Idle baseline 10 min: OS + lattice host without INV-63.
2. INV-63 idle: service up, `tick()` every `reconcile_interval_s` (120 s per `edge-site-a`), 10 converged namespaces.
3. Steady load: `perf/bench.py`-style noop reconcile loop at 10, 50, 100 req/s for 15 min each (`max_inflight=8`).
4. Burst: scale 1→200 and 200→5 (bench scenarios) ×20.
5. Offline mode: lattice partitioned for 1 h; measure offline_intent journal writes (fsync energy on flash).
6. Thermal: SoC temperature (`/sys/class/thermal`) every 1 s; ambient recorded; check throttling flags.
Each run ×3; report median.

## Metrics
Average and p95 power (W) above idle baseline; energy per request (mJ); energy per journal append; SoC temperature max and time-to-throttle; CPU frequency residency; flash write bytes/day (endurance).

## Pass criteria (proposed, pending owner approval)
- INV-63 idle overhead ≤ 0.5 W (E2/E3) and ≤ 1 W (E1) above baseline.
- No thermal throttling at 50 req/s sustained on E2 at 35 °C ambient.
- Flash writes ≤ 50 MB/day at the edge-site-a profile.
- Latency thresholds in `perf/thresholds.json` × `ci_slack_factor` (3.0) still met on E2.

## Deliverable
`perf/edge_power_results.json` (to be created when measured) + signed evidence; until then C068 remains open.
