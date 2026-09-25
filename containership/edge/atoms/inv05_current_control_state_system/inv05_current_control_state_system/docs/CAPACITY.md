# Performance baselines and capacity model

Traceability: C061–C070, C088; MC-042. **Caveat (EX-005):** numbers below were measured in the build sandbox (2 vCPU Intel Xeon @ 2.10 GHz, ext4 on virtio disk, Python 3.11.15), not on production hardware. Re-run `bench.py` on target hardware during Day-1 commissioning and replace this table; the release gate compares against the target-hardware report once present.

## Baseline (seed 42, value mix 70 % 64 B / 25 % 1 KiB / 5 % 16 KiB, mixed 45/40/12/3 write/read/CAS/range)

| Mode | Ops | Throughput (ops/s) | write p50 / p99 / max (ms) | CAS p50 / p99 (ms) | read p99 (ms) | range(100) p99 (ms) | watch delivery p99 (ms) | peak RSS |
|---|---|---|---|---|---|---|---|---|
| fsync WAL, 4 watchers | 20 000 | ≈ 3 000 | 0.52 / 1.05 / 4.4 | 0.53 / 0.97 | 0.02 | 0.85 | 1.5 | 38 MiB |
| group commit (32), 4 watchers | 20 000 | ≈ 7 000 | 0.14 / 0.98 / 4.1 | 0.15 / 0.98 | 0.02 | 0.79 | 4.6 | 38 MiB |
| memory only, 8 watchers | 50 000 | ≈ 6 000 | 0.13 / 1.13 / 4.5 | 0.14 / 1.25 | 0.03 | 1.9 | 22 | 68 MiB |

Raw reports: `evidence/bench/bench_*.json`; CI smoke run: `evidence/bench_smoke.json`. Compaction of ~11 k–28 k history events took 7–23 ms (holds the store lock; the controller rate-limits it).

## Thresholds (C062) — proposed release-blocking limits (C070)
| Metric | Threshold | Basis |
|---|---|---|
| txn p99 (fsync, target SSD) | < 10 ms (SLO) | REQUIREMENTS NFR |
| txn p99 regression vs last release | ≤ +20 % | CI smoke + Day-1 report |
| throughput regression | ≥ −15 % | CI smoke |
| watch delivery p99 at 8 watchers | < 50 ms | baseline × 2 |
| worst case (max) write | < 100 ms excluding compaction pauses | baseline |

The CI gate currently enforces an absolute smoke bound (write p99 < 50 ms on the CI runner) because runner hardware varies; relative regression checks activate once a target-hardware baseline is committed (EX-005).

## Capacity model (C069)
* CPU: a single Python process serialises commits under one lock; sustained write capacity ≈ 1 / (p50 commit time). Keep sustained load ≤ 60 % of measured throughput (headroom for compaction pauses and bursts).
* Memory: ≈ (live keys × avg(value+key+~200 B)) + (retained history events × avg event size ~ value + 300 B) + watch queues (≤ `max_watch_queue_events` per watch). With `retain_revisions=100 000` and 1 KiB values, budget ≈ 150 MiB for history.
* Disk: WAL grows ≈ (event bytes + 12 B frame + 16 B AEAD) per event until checkpoint every `checkpoint_every_records`; keep ≥ 2 × (snapshot + WAL generation) free (preflight checks 2 GiB default).
* Saturation signals: `cstate_inflight_requests` near `max_inflight_requests`, rising `cstate_request_duration_seconds` p99, `cstate_watch_backlog_events`, `cstate_history_events` near `max_history_events`, `process_resident_memory_bytes`.

## Optimisations applied / considered (C065, C066)
Applied: one revision per multi-op txn (batching); bisect-indexed sorted keys for ranges; catch-up paging reads directly from shared history (no per-watch copies); prefix filtering server-side. Considered, deferred: per-key version index arrays (avoid list rebuild in `_version_at`), sharded locks (would complicate linearizability), zero-copy framing.

## Per-tenant overhead (C064) and power (C068)
Per-tenant cost is per-identity token bucket (~100 B) and watch bookkeeping; namespace mapping adds one string concat per key. Power/thermal on edge nodes was not measured (no hardware) — EX-005.
