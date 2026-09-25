# GAP-11 runbooks (GAP11-P2-47)

**Status:** written, **not exercised**. Every runbook below needs a timed drill in a real environment (BLK-ENV) and owner sign-off (BLK-HUMAN) before GAP11-EXIT-08.
Commands refer to the reference implementation in `gap11_control/`.

## RUNBOOK-01 Bootstrap
1. Provision secret refs `secretref://gap11-authn`, `secretref://gap11-audit` in the KMS.
2. Start one controller; confirm `health_report().ready == False` until leadership is acquired.
3. Register inventory only from attested node agents (`AttestationVerifier.verify` must pass per device).
4. Confirm `ready == True`, `role == leader`, `store_revision > 0`. Record the audit head (`AuditLedger.head()`) in the external witness.

## RUNBOOK-02 Rollout / RUNBOOK-03 Rollback / emergency disable
- Rollout: one controller at a time; new controller joins as follower; `step_down()` the old leader; watch STALE_FENCE (must be 0 after handover) and `leader_change` events.
- Rollback: redeploy previous version; WAL format v1 is unchanged in 4.3.0, so rollback needs no data migration. Config: `ConfigManager.rollback()`.
- Emergency disable: `Controller.freeze(True)` — reads keep working, every mutation returns MAINTENANCE_MODE. Existing leases are untouched.

## RUNBOOK-04 Orphan reconciliation
Run `reconcile(liveness)`. Expected: dead → RECLAIMED (device stays DIRTY), alive → renewed, unknown → SUSPECT and reclaimed only after `lease_grace_s` of continued unknown. Never force-release a SUSPECT lease whose `suspect_reason` is DEVICE_MISSING.

## RUNBOOK-05 Store recovery
- `STORE_CORRUPT` on open: do **not** edit the WAL. Copy the store directory aside, restore the last snapshot + WAL from backup, reopen, run `LeaseStore.verify()`, then `reconcile()`.
- Disk full: commits return STORE_UNAVAILABLE and the partial append is rolled back; free space, no restart needed.
- Torn tail after crash: handled automatically on open (tail truncated, commit never happened).

## RUNBOOK-06 Failed scrub
Device is QUARANTINED with `quarantine_reason` (SCRUB_FAILED / SCRUB_TIMEOUT / SCRUB_OUTCOME_UNKNOWN). Re-run `scrub()`; a verified scrub is the only exit. Two consecutive failures → RUNBOOK-08.

## RUNBOOK-07 Device health / RAS
`set_health(device, health="failed")` quarantines. Reset storm (≥3 resets in 10 min) is classified failed by `HealthMonitor`.

## RUNBOOK-08 Device replacement
`set_draining(device, True)` → wait for leases to release → physically replace → the new board has a new stable_id and appears as a new device; the old record goes MISSING. A board that returns reappears QUARANTINED.

## RUNBOOK-09 Incident containment
Freeze mutations; export `AuditLedger.verify(expected_head=witness)`; snapshot the store directory read-only; collect telemetry by `trace_id`/`request_id`; do not unfreeze until the owner approves.
