# Constrained-Edge Characterization (MC-030)

**Status: PARTIAL.** Resource ceilings and offline behaviour are characterised from the reference host; **power/thermal** measurements require physical far-edge hardware and are OPEN.

| Property | Value (reference host, see `evidence/bench.json`) | Source |
|---|---|---|
| Memory per descriptor | ≈ 675 B (10 000 descriptors ≈ 6.8 MB peak) | bench `descriptor_density` |
| Host startup (policy + one preopen) | ≈ 0.2 ms | bench `startup_ns` |
| fd open/close via openat2 | p50 ≈ 4 µs | bench `fs_open_close` |
| Audit append with fsync | p50 ≈ 0.23 ms (storage-bound) | bench `audit_append_fsync` |
| Runtime dependencies | Python stdlib only; Node optional | SBOM |

**Offline operation:** no network dependency on the enforcement path; identity verification uses local keys; policy comes from the local `ConfigStore` (fails closed with `CONFIG_STALE` if absent).  
**Restart/replay:** config and audit are durable (atomic pointer, verified append-only log continuing its chain after restart — `Audit.test_durable_chain_and_reopen`).  
**Capacity model:** per-node slots via `Admission(node_slots, fair_share)`; per-tenant limits via `QuotaLedger`. Size `node_slots` ≈ available fds / (max descriptors per workload).  
**Open:** power draw, thermal throttling behaviour, ARM64 edge SoC figures, flash-wear impact of per-record fsync (consider batched fsync profile).
