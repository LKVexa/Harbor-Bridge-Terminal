# Non-functional requirements (INV30-GAP-011 · INV-30-C013, C017)

| Attribute | Requirement (semantic-model service, commodity x86_64/aarch64) | Evidence |
|---|---|---|
| Latency: access | p50 ≤ 1 ms, p95 ≤ 2.5 ms, p99 ≤ 5 ms (measured ~0.07 ms p50) | `evidence/RELEASE_EVIDENCE.json` benchmark |
| Latency: derive | p50 ≤ 1.5 ms, p99 ≤ 8 ms | same |
| Latency: model check | p50 ≤ 50 µs | same |
| Throughput | ≥ 5 000 authenticated access/s per core (measured ~11 500) | same |
| Availability | 99.9 % monthly for the service wrapper; invariants 100 % (zero budget) | SUPPORT_SLO.md |
| Durability | none by design — state is volatile; audit ledger fsync per event | STATE_AND_RECOVERY.md |
| Consistency | per-capability linearisable check/derive/invalidate | test_concurrency |
| Isolation | tenant-bound handles, per-tenant quotas | T-05, T-11 |
| Determinism | seeded fuzz; decisions derived only from request + config + state | test_properties |
| Recovery | re-bootstrap after emergency disable ≤ 1 s | bench recovery_ms |
| Capacity ceilings / quotas / fairness | `limits.py`; per-tenant token bucket in admission control | test_resilience |
| Hardware backend | **TBD** — thresholds cannot be set before a CHERI backend is measured (GAP-004) | — |
