# PLN-03 runbooks (MC-051)

Each runbook: trigger → checks → action → verify → record. All actions are audited by the plane.

## RB-01 Emergency disable
Trigger: SEV1 security or integrity event. Authority: OWNERS.yaml `emergency_authority.emergency_disable`.
1. `rt.emergency_disable(actor, reason)` → lifecycle `quarantined`, every call `PK_QUARANTINED`.
2. Verify `rt.health()["ready"] is False` and audit event `quarantine target=runtime`.
3. Recovery: new process from last good release (quarantine → draining → stopped is terminal by design).

## RB-02 Quarantine one adapter
`rt.quarantine_adapter(name, actor, reason)`; verify health shows adapter false; release with `release_adapter` after INV-49 clears it.

## RB-03 Freeze writes
`rt.freeze(actor, reason)` — reads continue. `rt.unfreeze(actor, reason)` to resume.

## RB-04 Config rollback
`store.rollback(author=..., reason=...)` (previous) or `rollback(to=N, ...)`; verify `health.config_digest` equals target digest in `store.ledger()`.

## RB-05 Partition / reconnect
During: watch `degraded_buffered` counter and buffer length. On `PK_READ_ONLY`: capacity exhausted, SEV2. After reconnect: `rt.reconcile()`; expect `remaining == 0`; `deduplicated` > 0 is normal.

## RB-06 Audit verification
`verify_chain(read_jsonl(path), seal_key)` must return `(True, "ok")`. Any failure: SEV1, preserve file, page security.

## RB-07 Fencing conflict
`PK_FENCED` in logs means a stale writer. Confirm current lease holder; stop the stale node; never lower epochs.
