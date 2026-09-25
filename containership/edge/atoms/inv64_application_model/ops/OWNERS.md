# Ownership and escalation — INV-64 (MC-04; C009)

Machine-readable source: `ops/owners.json` (roles, escalation timers, approval matrix, delegations). The production gate and `tools/governance_check.py` refuse certification while any role below has no assignee.

| Role | Accountable for | Assignee | Backup |
|---|---|---|---|
| inv64-component-owner | architecture, releases, Medium waivers | **unassigned** | inv64-backup-owner |
| inv64-backup-owner | cover for the owner | **unassigned** | — |
| inv64-security-contact | vulnerability intake, Critical/High security waivers (with owner), break-glass review | **unassigned** | platform-security-oncall |
| inv64-sre-oncall | paging, rollback, incident command until handoff | **unassigned** | platform-sre-oncall |
| architecture-review-board | ADRs, normative source changes, OAM baseline | **unassigned** | — |
| release-manager | production GO, signing ceremony | **unassigned** | — |

Assignees are role handles or team names (continuity), resolved by the owner
editing `owners.json`; review on every organizational change and at least
quarterly (access review).

## Escalation

| Severity | First responder (ack) | Then | After hours |
|---|---|---|---|
| SEV1 | inv64-sre-oncall (5 min) | owner +15 min, security +15 min, architecture +60 min | page |
| SEV2 | inv64-sre-oncall (15 min) | owner +60 min | page |
| SEV3 | owner (8 h) | — | next business day |
| SECURITY | security contact (1 h) | owner +2 h | page for Critical/High |

## Decision rights

| Decision | Approver |
|---|---|
| patch/minor release, Medium waiver, overlay schema change | component owner |
| authn/authz/trust/crypto change, Critical/High security waiver, break-glass grant | security contact (+ owner) |
| ADR, normative source change, OAM baseline, new platform tier | architecture-review-board |
| production GO, signing | release-manager (must not also administer the authz policy) |

Emergency delegation: owner/backup may delegate a role for ≤ 14 days via
`temporary_delegations` (role, delegate, expires, approved_by); expired
delegations are ignored automatically.

**Why nothing is filled in:** naming accountable people is the owner's
decision; this remediation pass did not invent assignees.
