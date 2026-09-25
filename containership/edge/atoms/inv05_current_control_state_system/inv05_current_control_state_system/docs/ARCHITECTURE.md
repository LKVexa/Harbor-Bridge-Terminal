# INV-05 Current Control-State System — Architecture (v4.3.0)

Traceability: C001–C010, C015, C018, C019; MC-001-08..11 (and the same generic scope items for every MC).

## 1. Responsibility (C001)

INV-05 owns the **control-state model**: a revisioned, multi-version key/value store that every controller reads and writes. Each committed transaction receives a new global revision; writes are compare-and-swap transactions with success/failure branches; consumers read at a revision and watch from a revision; compaction discards history and **explicitly refuses** any read or watch that needs discarded history so the consumer relists instead of silently accepting a gap.

## 2. Owns / does not own (C002)

| Owns (implemented here) | Module |
|---|---|
| Global revision numbering, MVCC versions, tombstones | `store.py` |
| Compare/success/failure transactions, typed predicates | `store.py` |
| Revision-aware point/range/prefix reads with stable pagination | `store.py` |
| Watch-from-revision with ordering, progress, resume, backpressure | `watch.py` |
| Compaction semantics and the retention controller | `store.py`, `backup.py::CompactionController` |
| Leases, TTL, fencing tokens | `store.py` |
| Durable single-member persistence (WAL + snapshots) | `wal.py` |
| Wire schemas, errors, negotiation | `schema.py`, `errors.py` |
| Namespace isolation, authn/authz enforcement at its own boundary | `security.py`, `service.py` |
| Audit trail, metrics, logs, traces, explanations of its own decisions | `audit.py`, `observability.py` |

| Explicitly does **not** own | Where it lives | Boundary artefact here |
|---|---|---|
| Consensus / membership | Approved external backend (MC-007) | `docs/CONSENSUS_CONTRACT.md`, `backend.py::ExternalBackendContract` |
| Cross-site replication policy | GAP-05 | `replication.py` (contract + fencing) |
| Controller logic | INV-04 and other consumers | client algorithm in `client.py` |
| Backup *scheduling/storage* | Platform backup service | `backup.py` produces/verifies/restores artefacts |
| Storage hardware, KMS/HSM, PKI issuance | Platform | `security.SecretProvider`, `wal.Keyring`, TLS file inputs |
| Organisational authorization policy authoring | Security team | versioned `Policy` documents consumed by `Authorizer` |

## 3. Dependencies (C003)

| Dependency | Direction | Failure behaviour (MC-xxx-10) |
|---|---|---|
| INV-04 Current orchestration | upstream consumer | Consumers get typed errors; `CSTATE_COMPACTED` ⇒ relist; `UNAVAILABLE`/`FROZEN` ⇒ back off per `retry_after_s`. |
| GAP-05 State replication | downstream | Stale epoch ⇒ `CSTATE_FENCED`; compaction beyond follower position ⇒ snapshot resync. |
| INV-07 GitOps transition layer | downstream reader | Reads at explicit revisions; compares desired vs. stored state. |
| PLN-03 Distributed runtime plane | peer / successor | Same wire protocol major 1; negotiated capabilities. |
| Filesystem (WAL/snapshots) | infrastructure | Any write/fsync error ⇒ store enters `FAILED` (fail-closed), readiness fails, no further acks. |
| Secret provider / KMS | infrastructure | Keys resolved at bootstrap; unavailable key ⇒ bootstrap refuses to start; running node keeps its unwrapped data key in memory only for process lifetime (ADR-005). |
| PKI / trust bundle | infrastructure | Missing or invalid ⇒ listener does not start on non-loopback (config validation). |
| `pk_core` framework | build/cert tooling | Optional at runtime; required for the 100-item framework gate (MC-001). |

## 4. Source of truth (C004)

The store's revision. A controller's cache is valid only up to the revision it last observed; any value without a revision is not authoritative. On a single member the WAL is the durable source of truth; in a replicated topology the approved consensus backend is, and INV-05 translates its revisions (ADR-002).

## 5. Assumptions (C005)

* Every peer, network path, disk and process can fail independently; clocks are not synchronised (leases use a monotonic clock; no correctness decision depends on wall-clock time).
* Callers are untrusted until authenticated; client-supplied keys never select a namespace.
* `fsync` is honest on the deployed storage; if not, the data-loss envelope in ADR-004 does not hold.
* Behaviour is identical whether a dependency is local or remote: all boundaries return the same typed errors.

## 6. Boundaries (C006)

Namespace = `tenant/env/site/workload`, bound to the authenticated identity (SPIFFE URI path). Server-side key mapping `/t/<tenant>/e/<env>/s/<site>/w/<workload>/<key>`; responses strip the prefix; watches are prefix-filtered server-side; rate limits and watch quotas are per identity; metrics carry no tenant labels; audit/explain records use pseudonymous subject hashes. Each site runs its own instance with its own epoch — nothing assumes a global singleton.

## 7. Mandatory vs optional (C007)

Mandatory: new revision per committed change; compare-before-apply; delivery of every change after a watch's start revision or an explicit error; scheduled compaction; refusal of reads/watches before the compaction point; fail-closed durability. Optional: batching (multi-op transactions), per-tenant limit tuning, additional backend adapters, encryption at rest (default **on**; may be disabled only with an approved exception).

## 8. Unsupported patterns / non-goals (C008)

Not supported: multi-writer active/active sites; using INV-05 as a blob store (1.5 MiB value cap); unauthenticated non-loopback listeners; `durability=none` in production; controllers that cache without revisions. Non-goals: implementing consensus, writing controllers, scheduling backups.

## 9. Lifecycle states (C015)

Service: `starting → recovering → ready ⇄ degraded → draining → stopped`; any state → `failed` on durability/corruption faults (terminal until operator recovery); operator overlays: `frozen(scope)`, `maintenance`, `quarantined`, `break_glass`. Key: `absent → live(version 1..n) → tombstone → (compacted) absent`. Lease: `granted → (keepalive)* → expired | revoked`. Watch: `catch-up ⇄ live → canceled(reason)`.

## 10. Intermittent connectivity (C018)

Clients resume watches from `resume_revision` after reconnect; if the gap was compacted they relist (normative algorithm in `client.py`). Lease holders that cannot reach the store must assume ownership is lost after `ttl` of their monotonic clock and must use `FENCE` compares for protected writes. Replicas beyond `max_safe_lag` report `safe_to_read = False`.

## 11. Precedence when requirements conflict (C019)

1. Safety/consistency (no lost acknowledged write, no silent gap) and tenant isolation.
2. Security (authn/authz, secret handling, residency).
3. Durability.
4. Availability / SLO.
5. Cost and performance.

A lower-ranked goal never overrides a higher one; e.g. the store fails closed (availability loss) rather than acknowledging a write it could not persist.

## 12. Accountable owner (C009)

See `docs/GOVERNANCE.md`. Owner names are **proposed** and must be confirmed by the package owner (exception EX-006).
