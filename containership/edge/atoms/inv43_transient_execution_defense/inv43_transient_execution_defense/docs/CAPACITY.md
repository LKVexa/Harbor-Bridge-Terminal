# Capacity model (item 36; C061, C065-C069)

Measured 2026-09-22 on the build sandbox (CPython 3.11.15, x86-64) by `bench/run_bench.py`; raw numbers in `evidence/perf/baseline.json`.

| Resource | Measured | Model |
|---|---|---|
| CPU per decision | p50 ≈ 0.13–0.15 ms, p99 ≈ 0.34–0.46 ms (single thread) | ~6,000 decisions/s/core in-process |
| CPU per intake | p50 ≈ 1.2 ms (HMAC verify + re-classify + audit fsync-free) | ~800 envelopes/s/core |
| Memory per node posture | ≈ 11.5 KB | 10k nodes ≈ 115 MB |
| Memory per retained decision | ≈ 7.5 KB (explain + in-memory audit) | explain store capped at 10,000 ≈ 75 MB |
| Storage | audit ≈ 0.4–0.6 KB/event | 1M decisions/day ≈ 0.5 GB/day |
| Network | envelope ≈ 6–8 KB per node per TTL | 10k nodes @ 300 s ≈ 270 KB/s |
| Kernel-entry cost baseline | getppid ≈ 183 ns on this host | not attributable per mitigation |
| Power / thermal / edge nodes | **not measured** | **BLOCKED** — no edge hardware |

Defect found by the capacity benchmark: the file-backed audit log kept every event in memory forever; it now keeps a bounded tail (`MEM_TAIL=1000`).

Avoidable work identified (C065/C066): `decide()` renders a full v2 report into every explain record (largest per-decision cost); batching SCH-01 candidate evaluation per node shares one freshness check; neither optimisation is applied in 4.3.0 because the p99 is already 4× under the proposed threshold.
