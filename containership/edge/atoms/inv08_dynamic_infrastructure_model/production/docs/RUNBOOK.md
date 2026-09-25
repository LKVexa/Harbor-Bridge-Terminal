# INV-08 production overlay runbook (generic)

Owners: all roles UNASSIGNED (`ownership.json`). This runbook has only been
exercised against local test doubles; no representative non-production
environment exists (verification of the procedure there is NOT_RUN).

## 1. Pre-activation checks
1. `python3 -B -m unittest discover -s inv08_dynamic_infrastructure_model/production/tests -t .` passes, also under `python3 -O`.
2. `python3 -m inv08_dynamic_infrastructure_model.production.pkcore_pin status` - currently exits 2 (pk_core UNRESOLVED): production activation is blocked.
3. `python3 -m inv08_dynamic_infrastructure_model.production.ownership` - exits 3 while roles are UNASSIGNED.
4. Evidence bundle: `python3 -m inv08_dynamic_infrastructure_model.production.evidence verify bundle.json --root . --require-approvals`.
5. Release gate: `python3 -m inv08_dynamic_infrastructure_model.production.ci.release_check --root dist --envelope provenance.json --key-file key.json` (fails closed without a production signer).
6. Waiver gate: `waivers.gate(...)` has no blocking items.

## 2. Deployment / activation
1. Take a signed backup of current state (`backup.write_backup`).
2. Run `rollout.rollout` stages 1% -> 10% -> 50% -> 100%; each stage passes the health gate (error rate, pool invariants).
3. Record each stage in the audit log (done by rollout.py when given an AuditLog).

## 3. Rollback
- Automatic when a stage gate fails; manual via the `abort` callback.
- After rollback `verify_rollback` must be true; otherwise escalate SEV2.
- State rollback: `backup.restore` into an isolated dir, validate, then swap.

## 4. Incident steps
1. Classify with `incident.classify(signals)`; page per `incident.escalation`.
2. Contain: `SafeModePool.frozen = True` (scale-in freeze); abort rollouts.
3. Recover: restore/reconstruct; `incident.recovery_validation` clean; unfreeze.
4. Post-incident: `PostIncident.record(audit)`; corrective actions need named owners.

## 5. Recurring
Governance reviews (`governance.status`), vulnerability SLAs (`vuln_policy`), waiver expiry alerts (`waivers.gate(...)["alerts"]`).
