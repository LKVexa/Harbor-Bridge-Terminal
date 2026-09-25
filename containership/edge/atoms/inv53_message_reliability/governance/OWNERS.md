# INV-53 ownership and escalation

**Status: UNASSIGNED.** No names are recorded. Binding people to roles is the owner's decision; the
exit gate (`python -m inv53_message_reliability gate`) blocks with `role <x> is UNASSIGNED` until every role
in `governance/owners.json` has a name, a backup, a contact route and a next-review date.

| Role | Accountable for | Name | Backup |
|---|---|---|---|
| service_owner | Outcome of the service, DLQ purge decisions, final escalation | UNASSIGNED | UNASSIGNED |
| technical_owner | Queue semantics, protocol, durability design | UNASSIGNED | UNASSIGNED |
| security_owner | Threat model, keys, authz model, vulnerability response | UNASSIGNED | UNASSIGNED |
| operations_owner | On-call, runbooks, config changes, emergency disable, redrive | UNASSIGNED | UNASSIGNED |
| qa_owner | Test suites, CI, certification evidence | UNASSIGNED | UNASSIGNED |
| release_approver | Promotion decision on the exit-gate bundle | UNASSIGNED | UNASSIGNED |

## Escalation chain
operations_owner (on-call primary) → technical_owner (secondary) → service_owner (incident commander at
SEV1/SEV2). Response targets per severity are in `docs/ops/INCIDENT_PLAYBOOK.md`.

## Decision rights
Machine-readable in `governance/owners.json` → `decision_rights`. Protocol changes need technical + security;
emergency disable may be invoked by operations_owner alone and is audited; DLQ purge is service_owner only.

## Stale-contact review
Every role carries `next_review`. The quarterly review (`docs/ops/REVIEW_PROGRAM.md`) re-confirms each
name; a departed owner's role is set back to `null`, which re-blocks the gate rather than leaving the
component silently orphaned. Do not put personal phone numbers or secrets in this repository — use
rotation identifiers in `contact_route`.
