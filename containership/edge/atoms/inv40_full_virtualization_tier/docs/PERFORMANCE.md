# Performance (INV-40-C061..C070, C088)

`tools/bench.py` produces `evidence/bench.json`: a reproducible baseline of the tier's **control-plane overhead** over `FakeProvider` (hypervisor time excluded). Real boot time, density, CPU/memory per guest on KVM, and power/thermal on edge nodes are **not measured** — no KVM host was available (blocker HW-KVM; EDGE-HW for C068; FLEET for fleet-scale C088).

Findings from the baseline (C065, C066):
* Each mutating op performs two `fsync`s (journal + audit). That dominates the ~3 ms p50 per op on the reference host — the serialization cost is durability, deliberately. Group-commit (batching fsyncs across concurrent ops) is the identified optimization; **not applied** because it changes acknowledgement semantics and needs an owner decision.
* No extra copies of guest images are made: disks are attached by path read-only.

Thresholds (C062, C070): `ci/bench_thresholds.json` is `status: PROPOSED`. `tools/ci.py` compares every run against it and reports regressions, but the gate counts unapproved thresholds as NO_GO.
Capacity model (C069): saturation signals are `admission.in_flight/max_concurrent_ops`, `waiting/max_queue`, shed counter, per-tenant quota headroom. A predictive model needs production telemetry (BLOCKED PROD-ENV).
Bounds (C067): queue, concurrency, quotas, journal compaction, log ring buffer (10k lines), decision store (5k), metric series (2k), QMP message (1 MiB), request (64 KiB).
