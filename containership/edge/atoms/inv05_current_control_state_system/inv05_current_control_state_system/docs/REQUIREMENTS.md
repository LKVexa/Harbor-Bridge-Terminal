# INV-05 Requirements, Invariants and Semantics

Traceability: C011–C017, C091; MC-*-09 (functional/non-functional requirements, invariants, safety and liveness).

## Source function translated into testable requirements (C011)

Source function: *desired-state persistence for Kubernetes* (etcd role). Each FR has an automated test.

| ID | Requirement | Verified by |
|---|---|---|
| FR-01 | Every committed mutating transaction advances the global revision by exactly one; all its mutations share that revision. | `test_store.TxnTest.test_one_revision_per_txn_and_per_op_results` |
| FR-02 | A transaction applies its success branch iff every compare holds at the evaluation revision, otherwise its failure branch; never a partial branch. | `TxnTest.test_failure_branch_executes`, `test_contenders_single_winner`, linearizability suite |
| FR-03 | Point/range/prefix reads at revision R return exactly the state as of R, or `CSTATE_COMPACTED` / `CSTATE_FUTURE_REVISION`. | `ReadApiTest.*` |
| FR-04 | Pagination is served from one revision across pages. | `ReadApiTest.test_pagination_is_stable_under_concurrent_writes` |
| FR-05 | Delete is distinct from writing null, creates a tombstone and a typed DELETE event; recreate starts a new incarnation. | `DeleteTest.*` |
| FR-06 | A watch from revision S delivers every retained change with revision ≥ S in order, or a terminal error with a resume point. | `test_watch.*`, `test_http.test_mirror_converges_under_writers_and_compaction` |
| FR-07 | Reads/watches before the compaction point are refused. | `test_compacted_start_refused`, conformance V009/V021 |
| FR-08 | Leases expire after TTL without keepalive, removing attached keys with EXPIRE events; fencing tokens are strictly increasing. | `LeaseTest.*` |
| FR-09 | Acknowledged writes survive process crash at every persistence boundary. | `test_durability.test_crash_at_every_persistence_boundary` |
| FR-10 | Namespaces are enforced server-side. | `test_service.IsolationTest.*` |

Deployment contexts (C012): cloud/datacenter run the same package; near-edge and far-edge use `storage.durability=fsync` (default) with smaller `compaction.retain_revisions` and the same protocol. There is no context-specific semantic difference.

## Non-functional requirements and SLOs (C013, C091)

| NFR | Target | Error budget | Evidence |
|---|---|---|---|
| Linearisable writes | 0 transactions applied with a failed compare | none | linearizability checker in CI |
| No silent gaps | every watch gets all retained changes or an explicit error | none | watch + mirror tests |
| Write latency (single member, fsync SSD) | p99 < 10 ms | 1 % may exceed | `bench.py --durable` report |
| Durability | 0 acknowledged writes lost with `fsync` class | none | crash tests |
| Availability (single member) | bounded by host; replicated availability owned by backend | — | ADR-002 |
| Isolation | 0 cross-namespace reads/writes/events | none | isolation tests, fuzz |

## Result semantics (C014)

* **Success** — `succeeded: true`, new revision.
* **Compare failure** — `succeeded: false`, failure branch applied (may be empty); not an error.
* **Partial success** — impossible by construction; ambiguous branches are rejected before execution.
* **Degraded** — admission frozen for a scope (`CSTATE_FROZEN`) or replica read-only; reads may continue.
* **Retryable failure** — error with `retryable: true` (`UNAVAILABLE`, `TIMEOUT`, `QUOTA`, `OVERLOADED`, `FROZEN`, `DRAINING`, `SLOW_CONSUMER`).
* **Terminal failure** — `retryable: false`; `CSTATE_FAILED` means the node is fail-closed and the outcome of the in-flight write is *ambiguous*: clients must re-read before retrying (idempotency-sensitive).

## Invariants (safety) and liveness

Safety (checked by `ControlStore.check_invariants()` after recovery/restore and in property tests):
S1 events strictly ordered by `(revision, index)`; S2 no retained event at or below the compaction revision; S3 per-key versions strictly increasing and ≤ head; S4 sorted index equals key set; S5 fencing counter ≥ every lease fence; S6 no acknowledged write absent after recovery.

Liveness: L1 a live watch receives a frame (events or progress) at least every `progress_interval`; L2 an expired lease is removed within one ticker interval; L3 compaction eventually runs when history exceeds `retain + margin` and no protection blocks it.

## Versioning (C016)

SemVer for the package; protocol `PK_CSTATE/<major>.<minor>` with append-only minors; events `cstate.event/1`; WAL records `v=1`; snapshots `cstate.snapshot/1`; backups `cstate.backup/1`. See `docs/COMPATIBILITY.md`.

## Capacity, quotas and fairness (C017)

All limits are in `limits.Limits` and `config.SCHEMA`; per-identity token bucket (rate + burst), per-identity watch quota, global in-flight gate, per-identity lease quota, bounded idempotency table, history ceiling. Fairness: each identity has an independent bucket, so one tenant cannot consume another's budget.
