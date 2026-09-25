# GAP-04 Capacity Model (C40)

Source of coefficients: `evidence/perf_baseline.json` (build host: 2 vCPU container, CPython 3.11.15, Linux 6.18, `/tmp` filesystem). **These are host-specific measurements, not production claims**; re-run `tests/perf/bench.py` on each supported hardware tier and re-derive (W-010). Calculator: `python -m gap04_disconnected_operation_controller.runtime.capacity --rate-per-min R --max-partition-h H [--sites N]`.

## Measured coefficients (build host)
| Quantity | Value | Notes |
|---|---|---|
| decide() latency p50 / p95 / p99 / max | 1.11 / 1.70 / 2.37 / 7.56 ms | two fsyncs per decision (decision + effect frame) |
| Single-writer throughput | ≈ 846 decisions/s | fsync-bound; CPU ≈ 0.77 s per 1k decisions |
| Journal bytes per decision | ≈ 1 799 B | encrypted decision + effect frames; plain record ≈ 751 B → write amplification ≈ 2.4× |
| Cold-start recovery | 0.03 s @100, 0.31 s @1k, 1.62 s @5k pending | linear ≈ 0.32 ms/decision |
| Reconcile payload to GAP-05 | ≈ 241 B/decision | 25 batches for 5k decisions; 0.80 s local processing |
| Reconnect storm | 25 nodes × 200 decisions: 0.96 s wall, 0 errors, 5 000/5 000 applied | single shared reference peer |
| 3-logical-day soak | 3 360 accepted, 960 refused by tier, full→sustain→freeze, 100 % reconciled | journal after compaction 4.2 KiB |
| Fleet instantiation | 100 nodes, 6.6 ms/node bring-up | in-process reference |

## Formulas
* Decisions per partition `D = rate_per_min × 60 × max_partition_h`; configure `max_decisions_per_partition ≥ 1.5 D`.
* Journal budget `journal.max_bytes ≥ 1.5 × D × 1 800 B + reserve_bytes`, rounded up to a power of two; `min_disk_free_bytes ≈ 25 %` of that.
* Memory for the pending log ≈ `1.5 × D × 1.5 KB`.
* Recovery time ≈ `2 × D × 0.32 ms` (degraded multiplier 2).
* Fleet reconnect drain ≈ `2 × D × sites / peer_throughput` — the GAP-05 peer, not GAP-04, is the fleet bottleneck; stagger reconnects (C43-014).

## Worked envelopes
| Profile | D | max_decisions | journal.max_bytes | recovery | note |
|---|---|---|---|---|---|
| 10/min, 24 h | 14 400 | 21 600 | 64 MiB | ≈ 9 s | **default `max_decisions_per_partition=10000` is too low** for this profile — raise it |
| 10/min, 72 h | 43 200 | 64 800 | 128 MiB | ≈ 28 s | |
| 60/min, 72 h, 500 sites | 259 200 | 388 800 | 1 GiB | ≈ 168 s | peer drain ≈ 36 h at 2 k/s ⇒ needs staggered reconnect + higher peer capacity |

Defaults (64 MiB, 10 000 decisions) therefore suit ≤ ~6 decisions/min for 24 h partitions.

## Saturation signals and behaviour before failure
`journal_utilization_ratio > 0.8` alert → budget exhausted ⇒ deterministic emergency freeze (control/audit frames still fit the reserve) → `max_decisions_per_partition` ⇒ `E0400` refusals → admission queue full ⇒ `E0700` shedding. None of these lose acknowledged decisions (tests `test_T_C20_*`, `test_T_C30_*`).

## Maximum supported scope
One `DisconnectedNode` per site state directory. Sites per GAP-05 peer is bounded by peer throughput (above), not by GAP-04. Not measured: ARM edge hardware, real WAN, power (W-010).
