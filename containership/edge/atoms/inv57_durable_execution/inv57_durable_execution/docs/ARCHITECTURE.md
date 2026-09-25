# INV-57 Durable Execution — Architecture, Requirements and Policies (v4.3.0)

**Status of this document: PROPOSED.** It was drafted during the v4.3.0 remediation pass. Nothing
in it is approved until an accountable owner (see `OWNERS.yaml`, currently unresolved) signs the
decision records below. The acceptance gate treats every item that depends on approval as not closed.

---

## 1. ADR-001 — Replay engine over a fenced, hash-chained history store (MC-02)

| Field | Value |
|---|---|
| Status | PROPOSED (no approver on record) |
| Context | v4.2.0 shipped a correct in-memory replay engine but no persistence, no ownership, no identity and no effect protocol. |
| Decision | Keep `durable.Worker` as the single replay engine. All persistence goes through the `HistoryStore` protocol, whose durable implementations commit each event through `_persist()` *before* it becomes visible. Every mutation is fenced by a lease epoch checked inside the same transaction. |
| Reference backend | `sqlite_store.SQLiteBackend` (WAL, `synchronous=FULL`). Approved scope: single-host deployments and backend-contract conformance. |
| Production backend | INV-50 state abstraction — **BLOCKED**, INV-50 not supplied. |
| Alternatives rejected | (a) Dapr Workflow runtime as the engine: the replay semantics would move out of this repository and could not be tested here. (b) Unfenced append with post-hoc dedupe: cannot prevent stale-owner commits. |
| Consequences | Replay stays O(n) with incremental chain validation. A stale worker can run user code but cannot commit its outcome. That leaves an in-doubt effect, which the effect protocol (§5) reconciles. |

## 2. SHALL-level requirements (MC-03)

| ID | Requirement | Verified by |
|---|---|---|
| R-01 | The engine SHALL append a durable `started` event before any activity code runs. | `test_durable`, `test_crash_boundaries` |
| R-02 | The engine SHALL NOT execute a completed activity again on replay. | `test_store::test_history_survives_process_restart_and_replays` |
| R-03 | The engine SHALL halt with `ActivityInDoubt` on a trailing `started` event and SHALL NOT re-run it automatically. | `test_crash_boundaries::test_every_boundary` |
| R-04 | The engine SHALL reject replay divergence before any new activity code runs. | `test_property::test_random_divergence_always_detected` |
| R-05 | A durable store SHALL reject any append whose lease epoch is not current or has expired. | `test_store::test_stale_owner_cannot_commit_after_takeover` |
| R-06 | A durable store SHALL reject appends whose sequence is not tail+1. | `test_store::test_conditional_append_rejects_out_of_order` |
| R-07 | A history failing integrity validation SHALL be quarantined, and only an operator SHALL release it. | `test_store::test_tampered_row_quarantines` |
| R-08 | Workflow identity SHALL be ASCII `[A-Za-z0-9._-]`, at most 128 characters per field, and SHALL be bound to the authenticated tenant. | `test_components::IdentityTests` |
| R-09 | Configuration SHALL be validated in full before activation, and SHALL NOT contain inline secrets. | `test_components::ConfigTests` |
| R-10 | Retries SHALL apply only to failures classified `after_backoff`; ambiguous outcomes SHALL NOT be retried. | `test_components::ResilienceTests` |

Deployment-context matrix: `dev`/`test` may use defaults. `staging` requires overlays. `prod` requires
`state_encryption_key_secret_ref` and forbids payload capture (enforced in `config.validate`).

## 3. Non-functional requirements (MC-04)

| NFR | Target (contract) | Measured (v4.3.0, this build machine only) | Status |
|---|---|---|---|
| Replay latency | p99 < 100 ms for 1000 events | see `evidence/benchmark/summary.json` (in-memory ≈ 3–4 ms p99; SQLite open+validate+replay ≈ 45 ms p99). v4.2.0 baseline: ≈ 3,700 ms | met on this machine |
| Replay scaling | linear | 4× events → < 8× time (gate test) | met |
| Durable append | not specified | ≈ 3.5k events/s (fsync on) | recorded, no target |
| Once-only effects | 0 duplicates | 0 in 16 real-process kill points (12 history + 4 effect-ledger) | met at reference scope |
| Edge power/thermal | — | not measured | BLOCKED (no hardware) |

## 4. Versioning and compatibility policy (MC-06, MC-15)

- History event schema `PK_WF_HISTORY_EVENT/2` is frozen. Any change is a new schema id, and the
  reader must support N and N-1.
- Backend schema version lives in the `meta` table. A reader **refuses** a newer version
  (`test_newer_backend_schema_refused`) and never downgrades it.
- Error codes (`errors.py`) are append-only. Codes are never reused.
- Lifecycle table changes that remove a transition are breaking changes.
- Package semver: breaking changes to the history, identity or error model require a major version.
- Cross-version peers: **OPEN**. No wire protocol between peers exists yet (depends on INV-53).

## 5. External-effect protocol (SG-04)

Effect id = `sha256(identity.key() # activity_id)`, known before dispatch. The engine records
`prepared` under the lease and then dispatches. Reconciliation of an in-doubt effect depends on its class:
`idempotent` → lookup, then an idempotent resubmit; `lookup_only` → lookup only; `unsafe` → operator.
Compensation is never automatic.

## 6. Constraint precedence (MC-09)

When constraints conflict: **integrity > once-only effects > tenant isolation > availability > latency > cost.**
Examples: a quarantined history stays down even under an availability SLO breach, and an in-doubt effect
halts the workflow even if the workflow then times out.

## 7. Boundary inventory (MC-10)

| Boundary | Format | Schema | Auth |
|---|---|---|---|
| History event | JSON | `schemas/history_event.schema.json` | store-level (INV-50: BLOCKED) |
| Workflow identity | JSON | `schemas/identity.schema.json` | bound to principal tenant |
| Error document | JSON | `schemas/error.schema.json` | n/a |
| Status document | JSON | `schemas/status.schema.json` | operator network only (RG-05 BLOCKED) |
| Configuration | JSON | `schemas/config.schema.json` | config ledger actor |
| Lifecycle control | call | `lifecycle.table()` | capability `workflow:control` / `operator` |

## 8. Threat model summary (MC-28, draft)

| Threat | Control in this repo | Residual |
|---|---|---|
| Duplicate effect after crash | started-before-run, in-doubt halt, effect ids | providers must honour effect ids |
| Stale/zombie worker commits | lease epoch checked in the append transaction | clock skew between hosts (the reference uses a single clock) |
| History tampering | SHA-256 chain, full check on load, quarantine; payloads deep-frozen in memory | the chain is **unkeyed**, so it detects accidents and partial edits but not an attacker who can rewrite the whole store (keyed MAC needs KMS, MC-33 BLOCKED); tail truncation is invisible to the chain, so the backup manifest records tails externally |
| Lease forgery | epoch + owner checked in-transaction | `Lease` is an unauthenticated value: a caller that knows owner name + epoch can act as that owner, so owner ids must be treated as secret or only trusted code can hold them (MC-11 BLOCKED) |
| Cross-workflow effect tampering | effect records scoped by workflow key on prepare and mark | — |
| Cross-tenant access | identity bound to principal; length-prefixed keys | no authn layer yet (MC-11 BLOCKED) |
| Secret leakage | secretref-only config; log field allowlist + redaction; unsafe error details hidden | no secret provider (MC-26 partial) |
| Log injection via identifiers | identity regex uses `fullmatch` (the first 4.3.0 draft used `$`, which accepted a trailing `\n`) | — |
| Resource exhaustion | history bound, admission control, circuit breaker | no per-tenant storage quota |
