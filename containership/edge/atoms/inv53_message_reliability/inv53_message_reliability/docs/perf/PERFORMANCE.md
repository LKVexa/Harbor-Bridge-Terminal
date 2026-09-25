# Performance: harness, thresholds, load shapes, capacity (C061–C070)

Harness: `python -m inv53_message_reliability bench [--n N] [--fsync] [--thresholds perf/THRESHOLDS.json]`
(`bench.py`): fixed seed 53, five load shapes (steady, burst, redelivery 30 % nack, large 16 KiB messages,
deep backlog) × two implementations (memory reference, durable journal). Reports p50/p95/p99/max/mean per
op, throughput, serialized bytes per message, peak traced memory per message and journal bytes.

## Baseline (CI evidence of this build; environment recorded in `evidence/CI_EVIDENCE.json`)
The authoritative numbers are in the evidence file for the exact source digest — they are not copied here
so this document cannot drift. Orders of magnitude observed in the 2026-09-22 cloud run (CPython 3.11):
memory ≈ 7–8 k msg/s with p99 ≤ 0.25 ms; durable (fsync off) ≈ 1.1–1.2 k msg/s with p99 ≈ 0.4–0.6 ms;
durable (fsync on) ≈ 0.5 k msg/s with p99 ≈ 1 ms.

## Optimisation plan and guarded fast paths (C066)
| # | Optimisation | Guard (what must stay true) | Status |
|---|---|---|---|
| O1 | Keep the journal fd open (unbuffered) instead of open/append/close per record | fail-stop on any write error; fd closed on close/compaction | done 5.1.0 |
| O2 | Epoch check by `stat` identity, full read only when `(ino, mtime_ns, size)` changes | fencing must hold under inode reuse + equal mtime | **withdrawn** — measured 1,005 → 1,465 msg/s together with O1, but the adversarial review reproduced a fencing bypass; the epoch is read on every append again (O1 alone: ≈ 1,140–1,210 msg/s). `test_epoch_fencing_holds_when_stat_identity_is_unchanged` |
| O3 | Group commit (one fsync per batch) | an op may be acknowledged only after its batch fsync | proposed |
| O4 | Avoid double deepcopy on receive | consumer mutation must still not reach broker state | proposed |

## Resource-bound model (C067)
Memory per queue ≈ peak_bytes_per_msg × (ready + in_flight + dlq), bounded by the three hard limits; journal
growth is bounded by `compact_every`; metric series by `max_series`; nonces by `nonce_cache`. With defaults a
queue's worst case is (100k + 10k + 100k) messages × max_message_bytes.

## Capacity model (C069)
Single queue throughput is serialized by one lock and one journal: `capacity_model.single_queue_max_msgs_per_s`
in the evidence. Saturation predictor: utilisation = offered rate × seconds_per_msg; shed above 0.8. Queues
scale horizontally (independent stores).

## Not measured (stated, not faked)
Power/thermal (C068) — no RAPL/IPMI access; per-tenant CPU accounting (C064) — only request counts per tenant
(`inv53_ops_total{tenant=…}`); context-switch profile (C065) — no perf counters; fleet-scale soak (C088).

## Regression gate (C070)
`bench.gate` compares a run with `perf/THRESHOLDS.json`. Thresholds are **PROPOSED** (no owner), so a met
threshold reads `MET_UNDER_PROPOSED` and the exit gate treats unapproved thresholds as a blocker.
