# GAP-01 Capacity, Quota and Performance Model

## Enforced ceilings (config knobs, validated ranges in `config.SCHEMA`)

| Resource | Knob | Default | Enforcement | Signal |
|---|---|---|---|---|
| Resident workloads | `max_workloads` | 512 | `E_CAPACITY` on admit | `gap01_resident_workloads` |
| Health signals | `max_health_signals` | 64 | registry refuses | — |
| In-flight requests | `max_queue_depth` | 256 | `E_RATE_LIMITED` | `gap01_requests_total{code="E_RATE_LIMITED"}` |
| Request size | `max_request_bytes` | 64 KiB | `E_BAD_REQUEST`, socket read bounded | — |
| Per-caller rate | `rate_per_second` / `rate_burst` | 50 / 100 | token bucket | same |
| Replay/idempotency window | `replay_window` | 4096 | bounded LRU, compacted file | — |
| Tracer ring | fixed | 1024 spans | deque | — |
| Process memory | systemd `MemoryMax` | 256 MiB | cgroup | cgroup metrics |
| Tasks/FDs | `TasksMax` / `LimitNOFILE` | 256 / 4096 | kernel | — |

## Measured baselines (`evidence/bench.json`, `evidence/soak.json`, CI container, Python 3.11)

| Measure | Result | Approved threshold (`tools/perf_gate.py`) |
|---|---|---|
| admit p50 / p99 (no fsync, 500 workloads) | ≈1.8 ms / ≈3.2 ms | p99 ≤ 10 ms |
| admit p99 (fsync) | ≈3.8 ms | ≤ 25 ms |
| status p99 | ≈0.2 ms | ≤ 5 ms |
| drain per workload (fake runtime) | ≈0.005 ms | ≤ 1 ms |
| restart recovery | ≈10 ms | ≤ 1 s |
| metrics render | ≈0.14 ms | ≤ 20 ms |
| soak: 20 nodes × 30 s churn | ≈350 ops/s, 0 invariant violations, audit chains intact | 0 violations |

Per-node boot memory: 300 successive boots showed no retained growth (tracemalloc). Soak growth is from bounded rings filling on the live fleet.

Numbers are from a shared cloud container and are indicative; re-baseline on each target platform (PLATFORMS.md) before approving thresholds for that tier. Power/thermal impact is not measured (EXC-008).

## Saturation signals

Rising `E_RATE_LIMITED`, request p99 > 50 ms, `under_pressure=1`, and resident workloads within 10 % of `max_workloads` predict saturation.

## Profiles

| Tier | `partition_lease_s` | `partition_max_autonomy_s` | `max_workloads` |
|---|---|---|---|
| cloud / DC | 30 | 600 | 512 |
| near-edge | 90 | 3600 | 256 |
| far-edge (intermittent links) | 300 | 86400 | 64 |

## Fairness

Within one node, drain order is deterministic (trust class then name), and per-caller token buckets prevent one caller starving another. Cross-tenant fairness of *admission* is a scheduler responsibility (ADR-0001); GAP-01 does not reorder admissions.
