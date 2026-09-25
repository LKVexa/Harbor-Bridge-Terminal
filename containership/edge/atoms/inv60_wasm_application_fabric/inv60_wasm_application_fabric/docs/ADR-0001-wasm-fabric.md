# ADR-0001 — Wasm application fabric: wasmCloud-shaped lattice behind a hardened control plane

- **Status:** proposed  (lifecycle: proposed → accepted → superseded | deprecated)
- **Date:** 2026-09-22
- **Deciders (required before `accepted`):** architecture owner, security owner, operations owner — *not yet recorded* (see `OWNERSHIP.json`, waiver W-APPROVALS)
- **Supersedes:** none. **Superseded by:** none.
- **Links:** `docs/REQUIREMENTS.md`, `SUPPORT_MATRIX.json`, `docs/THREAT_MODEL.md`, `docs/COMPATIBILITY.md`

## Problem and scope
INV-60 must run content-addressed Wasm components across a lattice of hosts, link them to capability providers by link name at run time, route calls across hosts and fail components over when a host is lost (contract.py). The fabric does **not** own deployment specs (INV-63), provider implementations (INV-65), artifact signing (GAP-07) or the component model (INV-10).

## Decision drivers
Artifact integrity with no error budget; failover ≤ 10 s; p99 routing overhead < 3 ms; edge/disconnected sites; tenant isolation; small operational footprint.

## Decision
Adopt **wasmCloud** (hosts + NATS lattice + wadm) as the production substrate, and put a repository-owned **control plane** (`fabric/`) in front of it that enforces what wasmCloud leaves to policy: authenticated/authorized operations, signature + provenance admission, lifecycle state machines, residency-aware placement precedence, quotas, deadlines/retries, leases with fencing, a tamper-evident audit ledger and a structured result model. Execution is behind the `ExecutionBackend` seam: `NodeWasmBackend` (real WebAssembly via V8, import-free) is the verified reference tier; `WasmCloudBackend` is the production seam and fails closed until a pinned lattice exists.

**Expected from wasmCloud:** host runtime, WIT component linking, NATS transport and its encryption, wadm reconciliation. **Owned here:** everything in `fabric/` and the evidence/gate tooling.

## Alternatives considered
| Option | Why not chosen (now) |
|---|---|
| Direct WASI runtime orchestration (wasmtime/WAMR + own scheduler) | Re-implements lattice transport, linking and reconciliation; highest build cost. Remains the fallback if wasmCloud is invalidated. |
| Kubernetes-native controllers (runwasi/SpinKube) | Brings back the control-plane weight this series is moving away from; poor at disconnected edge. |
| microVM / full VM isolation (Firecracker) | Stronger isolation, but 10–100× start latency and memory per workload; kept for untrusted-tenant tiers. |
| Other component platforms (Spin/Fermyon Cloud) | Less mature multi-host lattice/failover semantics for edge. |

## Dependencies introduced
NATS (JetStream for durable control state), wadm, WIT / Component Model (WASI 0.2), wasmCloud host. Pins: `SUPPORT_MATRIX.json` (all currently `untested`).

## Trade-offs
Security: strong capability model, but NATS becomes a critical trust boundary (TM-T05/T06). Portability: WIT/WASI are open standards; wasmCloud-specific APIs are isolated behind `ExecutionBackend`. Latency: one NATS hop per cross-host call. Availability: NATS cluster quorum becomes a dependency; isolated-serving mode bounds the impact. Lock-in: moderate, mitigated by the seam.

## Reconsideration triggers
wasmCloud or NATS unmaintained / licence change; measured p99 overhead > 3 ms on target hardware; inability to meet tenant isolation for untrusted tenants; WASI 0.2/0.3 incompatibility.

## Reversibility / migration
All control-plane semantics live in `fabric/`; replacing the substrate means implementing a new `ExecutionBackend` and transport adapter and re-running `tests/` plus the (future) M24 integration suite.
