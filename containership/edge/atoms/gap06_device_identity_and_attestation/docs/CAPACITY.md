# Capacity baseline (MC-26/39) — measured, not approved

Environment: Python 3.11.15, 2 vCPU, Linux-6.18.44-fc-v37-x86_64-with-glibc2.39.

| Measure | Value |
|---|---|
| attest path p50 / p99 / max | 4.978 / 11.19 / 12.946 ms |
| throughput (single process, fsync off) | 182.2 /s |
| traced memory per attestation | 1252 bytes |
| challenge table across soak rounds | [71, 71, 71] (bounded: True) |
| idempotency rows after soak | 1600 — **unbounded, no retention implemented** |

Known scale limits: `DurableStore` holds every table in memory and `items()` deep-copies a table (O(n)), which `ChallengeBook.issue` calls on every issuance — acceptable for the reference, not for a fleet. Sharding: `ops.ShardRing` (consistent hashing, tested for balance and ≤35% movement on 4→5 shards). Thresholds for release are **not approved** (no owner).
