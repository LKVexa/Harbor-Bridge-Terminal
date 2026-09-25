# Performance engineering  (components 62-71)

- **Harness (62):** `bench/harness.py` — fixed-seed workloads, warm-up, environment capture, p50/p95/p99, throughput, JSON evidence (`evidence/benchmark.json`).
- **Thresholds (63):** `bench/thresholds.json` (PROPOSED). Contract SLO: append p99 < 2 ms.
- **Load profiles (64):** small-message log append, 8-subscriber fan-out, 64 KB fan-out, durable fsync never/always. Soak, burst and fleet-scale: **UNVERIFIED** (no long-running environment).
- **Per-tenant accounting (65):** `QuotaManager.snapshot()`.
- **Copy/serialisation analysis (66):** fan-out uses `deepcopy` per subscriber for isolation. Measured finding: deepcopy *shares immutable leaves*, so a 64 KB string payload costs about the same as a small dict (0.008 ms vs 0.019 ms p50 for 8 subscribers on the build host) — isolation is preserved because strings are immutable; mutable containers are copied. Size accounting serialises once to JSON (`_size`). A zero-copy path for large payloads is INV-37's job (bulk data plane); messages carry references.
- **Optimisation layer (67):** batching (`poll(limit)`, adapter `consume(max_messages)`), fsync `batch` policy, idempotent producer on Kafka. Further optimisation deferred until target-hardware numbers exist (PARTIAL).
- **Bounded controls (68):** see `CAPACITY.md`.
- **Edge power/thermal (69):** **UNVERIFIED** — requires physical edge devices and power instrumentation; nothing measured.
- **Capacity model (70):** `quota.saturation()`; health `ready=false` at saturation.
- **Regression gate (71):** `bench/harness.py --gate` exits 1 when any p99 exceeds its threshold; wired in CI.
