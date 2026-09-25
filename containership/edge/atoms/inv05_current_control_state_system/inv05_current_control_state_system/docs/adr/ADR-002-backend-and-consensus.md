# ADR-002 — Production backend and consensus boundary

* Status: **Proposed / BLOCKED on owner decision** (EX-001) · Traceability: C010, C031, C055, C058, C093, MC-004, MC-005, MC-007

## Decision (proposed)
1. Supported today: `LocalBackend` — single member, fsync WAL, no consensus. Allowed topologies: single-site, single-writer, with backup/restore for DR (RPO = last verified backup, RTO per `docs/DR_PLAN.md`).
2. For multi-member HA the owner must select and pin an external consensus backend in `deploy/backend_pin.json` (candidate: etcd v3.5.x/3.6.x, N/N-1 support). `ExternalBackendContract.connect()` refuses to start until the pin is `APPROVED` with version, SHA-256 and required features — **no simulated backend evidence is produced**.
3. The adapter must satisfy `docs/CONSENSUS_CONTRACT.md` and pass the same conformance vectors and linearizability suite as the local engine.

## Consequences
Production HA certification (MC-004/005/007, P0) remains blocked until the pin is approved and the adapter is implemented and tested against a real multi-node deployment.
