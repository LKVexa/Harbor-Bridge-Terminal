# Outcomes and lifecycle (C014, C015)

Machine-readable: `ERRORS.json` (catalog, generated from `errors.py`), `ops/lifecycle.json` (generated from `lifecycle.py`).

## Outcome taxonomy (closed)
| Outcome | Blob may exist | Metadata committed | Entropy injected | Guest may run | Cleanup |
|---|---|---|---|---|---|
| success (capture) | yes | AVAILABLE (+ idempotency result + quota index, one transaction) | n/a | n/a | none |
| success (restore) | yes | grant READY with recorded result | yes, acked | yes | none |
| degraded_success | as success | as success | as success | as success | reserved: no path currently emits it (telemetry outages never degrade an operation's outcome) |
| partial_success | — | — | — | — | reserved; capture is all-or-nothing by design |
| retryable_failure | capture: no (deleted or reconciled) | capture: retired to history; restore: grant FAILED+retryable | restore: maybe | **no** — destroyed | automatic; same idempotency key may retry (max 3 attempts per grant) |
| terminal_failure | no | nothing new | no | no | none |
| policy_rejection | untouched | nothing | no | no | none — refused before side effects |
| integrity_rejection | untouched (quarantine on scrub) | nothing / QUARANTINED | no | **no** — destroyed if loaded | quarantine for review |
| operator_aborted | untouched | nothing | no | no | none |

Retryability comes only from the catalog (`ErrorSpec.retryable`), never from exception text. Every outcome
emits: stable code, `inv26_requests_total{op,outcome,code}`, a structured log line, an audit decision record.

## Snapshot lifecycle
`ABSENT → CAPTURING → CAPTURED → VERIFYING → AVAILABLE ⇄ QUARANTINED → DELETING → DELETED`, with
`CAPTURING|CAPTURED|VERIFYING → FAILED` (retired to `snaphist/` so the id can be retried).
Persistent writes: CAPTURING (+idempotency reservation +quota index) → CAPTURED (blob durable) → VERIFYING →
AVAILABLE (commit). Guards: only `AVAILABLE` is restorable; QUARANTINED → AVAILABLE needs
`snapshot.quarantine`, and integrity quarantines need break-glass.

## Restore lifecycle (per grant)
`PENDING → RESTORING → RESEEDING → READY`; any of the three may go to `FAILED`. **READY is reachable only
from RESEEDING, only after the injector acknowledged the seed**; any failure after the guest was loaded
destroys it.

## Concurrency rules
| Pair | Rule | Mechanism |
|---|---|---|
| capture vs capture (same id) | exactly one wins, others SNAP_DUPLICATE | CAS on `snap/<id>` expect-absent |
| capture vs restore | restore only sees AVAILABLE | state check under CAS generations |
| restore vs restore (same grant) | at most one commits | CAS on `grant/<sha256(nonce)>` |
| restore vs restore (different grants) | independent | per-grant keys |
| delete vs restore | delete wins; in-flight restores fail closed (NOT_FOUND / illegal transition / KEY) | generation CAS + crypto-erase |
| admin quarantine vs restore | quarantine wins for new restores | state check |
| multi-controller | lease + monotonic fencing token; stale writer gets SNAP_FENCED | `MetaStore.acquire_lease` |

## Timeouts and crash recovery
Per-state budgets in `ops/lifecycle.json`; older in-flight ops are reported by `stalled()` and the
`inv26_stalled_operations` gauge. On restart `reconcile()` applies `lifecycle.recovery_action`: interrupted
captures → FAILED (blob GC), interrupted deletes → completed, interrupted restores → FAILED (retryable); orphan
blobs removed. Verified by the crash-at-every-write matrix in `tools/faults.py`.
