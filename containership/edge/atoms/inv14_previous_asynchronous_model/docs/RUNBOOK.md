# INV-14 Runbook (v4.3.0)

Every step below has an executable form in `tools/runbook.py`; the commands are
exercised by `tests/test_p2_components.py::C33Runbook` against a sandbox state
directory. Paging/escalation targets come from `governance/OWNERS.json`, which is
**UNASSIGNED** in this build — production activation is blocked until it is filled.

## R0 Activation
1. `python3 verify_release.py` — must exit 0 (exit 2 = blocked; read the listed blockers).
2. `python3 tools/sign.py verify --require-trusted` — must print `OK:TRUSTED`.
3. `python3 tools/runbook.py --state DIR status` — lifecycle `DEPRECATED`, pk_core `PK_CORE_OK`.

## R1 Verification after change
`python3 tools/run_evidence.py --out evidence` then compare `evidence/CHECKLIST_STATUS.json` with the previous release.

## R2 Emergency disable / containment
`python3 tools/runbook.py --state DIR disable --actor NAME --reason TEXT` — new polls refused at once
(`PK_POLL_DRAINING`), in-flight polls finish (≤ 60 s), then `DISABLED`. Quarantine (no re-enable without
review): `... transition QUARANTINED`.

## R3 Cross-owner or identity refusals
Alerts `Inv14CrossOwnerAttempts`, `Inv14IdentityRefusals`. Verify audit chain:
`python3 tools/runbook.py --state DIR verify-audit`. Identify tenant from the alert label, pull the audit
records by correlation id, revoke/rotate the issuer key if forged tokens are seen, quarantine if active abuse.

## R4 Saturation
`Inv14Saturation`. Check `status` admission snapshot; raise limits only through a new config version
(`config.ConfigStore.update`), never by editing code. Prefer migrating the heaviest tenant to INV-15.

## R5 Invalid requests
Caller defect. The error code identifies the field; notify the consumer owner from the migration registry.

## R6 Timeout load
Informational; producers idle or timeouts too short. No action unless paired with R8.

## R7 Migration regression
A MIGRATED or unregistered consumer is using the legacy path. Check `governance/MIGRATION_REGISTRY.json`;
roll the consumer's migration back (`MigrationStateMachine.rollback`) or add a waiver with a different approver.

## R8 Software defect
p99 latency high or unstructured errors in logs. Capture diagnostics (`status`), disable (R2) if lost wakeups
are suspected, reproduce with `tools/interleave.py` and `tools/soak.py`.

## R9 Rollback
Re-enable after disable: `python3 tools/runbook.py --state DIR rollback --actor NAME --reason TEXT`
(DISABLED → DEPRECATED). Release rollback = redeploy the previous signed archive and verify its manifest.

## R10 Recovery validation
After restart: `status` shows the restored checkpoint counters and `readiness_persisted: false`;
run `python3 tools/faults.py F6_process_kill F7_corrupt_checkpoint`.
