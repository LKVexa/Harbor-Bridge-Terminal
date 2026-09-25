# INV-08 incident response

Model and tooling: `production/incident.py`.  Owners: UNASSIGNED (see 08_raci.md);
paging is modelled only - no pager integration exists.

## Severity
| Sev | Trigger (INV-08 specific) | Ack | Page |
|---|---|---|---|
| SEV1 | busy node reclaimed; size > max_nodes; audit chain broken | 5 min | oncall_primary, incident_commander, service_owner |
| SEV2 | > 1 consecutive failed scale decision; lease store unavailable | 15 min | oncall_primary, incident_commander |
| SEV3 | leaked (unleased) provider nodes accruing cost; > 50% responsiveness budget used | 60 min | oncall_primary |
| SEV4 | isolated retryable provider error | next business day | none |

Escalation: every missed ack interval moves one step up `escalation_chain`.

## Containment / safe mode
1. Engage scale-in freeze (`SafeModePool.frozen = True`): reclaims are suppressed, leases renewed, max bound still enforced.
2. Stop rollouts (rollout.py `abort`) and roll back if a release is in flight.
3. Preserve evidence: `audit.verify_file`, checkpoint, backup (`backup.write_backup`).

## Recovery and validation
1. Restore or reconstruct state (`backup.restore` / `backup.reconstruct`), resolve LEAKED/LOST nodes.
2. `incident.recovery_validation(pool, expected_busy=...)` must return no problems.
3. Unfreeze; watch one full lease TTL of ticks with invariants green.

## Post-incident
`PostIncident` record: monotonic timeline, corrective actions with owner and due
date (UNASSIGNED owners are reported as blockers), appended to the audit log.
Postmortem within 5 business days for SEV1/SEV2.
