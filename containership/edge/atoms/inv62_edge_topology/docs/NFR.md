# Non-functional requirements envelope (MC-005, C013)

Status: engineering proposal; numeric targets marked *(proposed)* need owner approval (see `OWNERSHIP.md`).

| Quality | Requirement | Evidence |
|---|---|---|
| Latency (engine) | nearest query p99 < 1 ms up to 10 000 nodes (contract SLO) | `perf/baseline.json`, perf gate |
| Latency (wire) | full authenticated resolve p99 ≤ 2.5 ms at 1 000 nodes *(proposed)* | perf gate |
| Partition continuity | a partitioned site can grant a lease within one status+acquire round trip; contract target 5 s | `test_integration`, `test_faults` |
| Availability | per-site instance; reads continue while FROZEN; resolution continues while partitioned (degraded) | `lifecycle.ALLOWED`, tests |
| Durability | every accepted mutation is fsync'd to the WAL before it is visible (`audit_fsync=true`, required in prod) | `persistence.py`, `test_persistence` |
| Consistency | single writer per site instance; revisions strictly increase; CAS via `expected_revision`; readers see whole batches | `test_concurrency` |
| Isolation | per-tenant graphs, quotas, admission buckets, lease keys; explicit tenant grants | `test_security` T06/T10 |
| Determinism | same inputs → same answer (tie-break by name); bootstrap is byte-identical across hosts | fuzz + bootstrap tests |
| Integrity | WAL, snapshot and audit MAC-chained; tampering refuses start | `test_persistence`, `test_security` |
| Scale envelope | defaults: 10 000 nodes, 50 000 links, degree 1 024, 64 caps/node, 1 024 tenants per instance | `config.DEFAULTS` |
| Recovery | WAL replay of 1 000 records ≤ 2 s *(proposed)* | perf gate |
| Resource | ≤ 64 KiB heap per small tenant *(proposed)*; bounded caches everywhere (replay 100 k, idempotency 50 k, decisions 10 k, logs 10 k, spans 5 k) | perf gate, code |
| Environmental | power/thermal on constrained devices: **NOT MEASURED** (MC-058 open_external) | — |

Deployment contexts: **cloud / datacenter** — one instance per region or DC acts for its sites' cloud side;
**near-edge** — one instance per site gateway; **far-edge** — devices are graph members only and never run
the authority (they hold node-agent credentials at most).
