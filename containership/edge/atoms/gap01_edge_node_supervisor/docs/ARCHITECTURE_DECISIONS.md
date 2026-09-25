# GAP-01 Architecture Decision Records

Status key: **Accepted** (implemented in v5.0.0) · **Proposed** (needs owner approval) · **Deferred** (tracked in `EXCEPTIONS.md`).
Approval of every record below is pending the component owner (EXC-001); "Accepted" means implemented and tested, not signed off.

## ADR-0001 — Authority boundary: local lifecycle authority only

**Context.** GAP-01 must be the single local authority for node lifecycle while not duplicating placement (scheduler), isolation (execution plane), discovery (GAP-02) or membership (control plane).

**Decision.**

| Decision | Local (GAP-01 decides) | Delegated | Prohibited |
|---|---|---|---|
| Lifecycle transitions | yes: legality, guards, stop-with-residents refusal | — | declaring healthy without evidence |
| Placement acceptance | yes: refuse admits unless ready + healthy + not cordoned/partitioned/pressured/emergency | where to place: scheduler | choosing a destination for drained work |
| Health | aggregation of registered signals | signal production: reporters | self-certifying health |
| Drain | order (trust class), deadlines, force-kill, proof of reclaim | termination mechanics: runtime adapter | reporting stopped with unproven reclaim |
| Hardware inventory | local read-only view for ceilings/pressure | authoritative discovery: GAP-02 | provisioning/decommission |
| Membership | local partition state machine | membership: control plane | acting as a control-plane member |

**Consequences.** Every "prohibited" row has a test (see `TRACEABILITY.json`).

## ADR-0002 — Persistence: checkpoint + write-ahead journal on local filesystem

**Decision.** `StateStore` keeps a checksummed JSON checkpoint (`state.json`, previous copy `state.json.prev`) and a per-record-checksummed write-ahead journal. Writes are temp-file → `fsync` → `rename` → `fsync(dir)`. Torn journal tail is discarded; corruption before the tail fails closed (`E_STATE_CORRUPT`). A monotonic `generation` numbers every durable change and scopes cordon acknowledgements.

**Rejected.** SQLite (extra failure modes on constrained/removable media, no need for queries); etcd/remote store (supervisor must work while partitioned).

## ADR-0003 — Control transport: signed JSON lines over a 0600 UNIX socket

**Decision.** Local IPC only. Each request is HMAC-SHA256 signed by a per-caller key, carries `request_id` (idempotency), `nonce` (replay) and `ts` (±`request_skew_s`). Probes (`/livez`, `/readyz`, `/metrics`) bind loopback only and are read-only.

**Deferred.** mTLS/SPIFFE workload identity for remote callers (EXC-003). Rationale: no remote caller is in scope for v5.0.0; the HMAC scheme is transport-agnostic and survives a later TLS wrapper unchanged.

## ADR-0004 — Runtime integration through an adapter protocol with reclaim proof

**Decision.** `RuntimeAdapter` = launch/stop/kill/inspect/list/reclaim_proof. A workload leaves the resident set only when `reclaim_proof.proven` (terminated **and** resources released). Shipped: `ProcessAdapter` (POSIX process groups, real) and `FakeRuntime` (deterministic fault injection).

**Deferred.** wasmtime, Firecracker and unikernel adapters (EXC-004). They plug in behind the protocol without controller changes.

## ADR-0005 — Failure model: fail closed, contain, degrade explicitly

**Decision.** Named degraded modes with explicit allowed-operation sets: `partitioned` / `autonomy-expired` (control plane silent), `emergency` (fail-safe; entered on autonomy expiry, watchdog stall, persistence failure after apply, or operator/break-glass), `pressure` (admission and uncordon blocked), `disabled` (persistent file flag; status only), `recovery mode` (bootstrap failure; never placement-ready). A restart never returns a node to `ready` on its own: `ready` becomes `cordoned` until health is re-established.

## ADR-0006 — Time

Supervisor decisions use a monotonic integer-second clock (`MonotonicClock`). Wall clock is used only for request freshness and audit timestamps. Health/drain timestamps that regress are rejected; future-dated evidence is invalid. Deadlines are owned by the supervisor (drain scheduler), not callers.

## ADR-0007 — Language and dependencies

Python ≥ 3.10, standard library only at runtime. Rationale: minimal supply-chain surface on edge nodes, reproducible builds, auditability. Cost: interpretive overhead (see `evidence/bench.json`; well inside thresholds) and no native TPM/seccomp bindings (EXC-002, EXC-005).
