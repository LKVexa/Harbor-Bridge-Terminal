# Ownership and escalation — INV-03 (checklist item 55)

**Status: UNASSIGNED.** Binding real people to these roles is the owner's decision and is not made here.

| Role | Holder | Holds capability |
|---|---|---|
| Accountable owner | UNASSIGNED | approves ADRs, release gate, retention policy |
| Security admin | UNASSIGNED | `baseline.install`, `baseline.rollback`, `emergency.toggle`, `quarantine.execute` |
| Exception approver (≥2 people) | UNASSIGNED | `exception.approve`, `exception.revoke` |
| On-call (primary / secondary) | UNASSIGNED | runs RUNBOOKS.md and INCIDENT_PLAYBOOK.md |

Rules enforced in code whatever the assignment: a service principal cannot hold `exception.approve`,
`baseline.install` or `emergency.toggle`; a requester cannot approve or renew their own exception.

Escalation path (to be completed with names): on-call → security admin → accountable owner, 15 / 30 / 60 minutes for a SEV1.
