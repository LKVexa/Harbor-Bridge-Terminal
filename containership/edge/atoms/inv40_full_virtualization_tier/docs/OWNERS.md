# Ownership and escalation (INV-40-C009) — **UNASSIGNED**

The roles, authorities and escalation mechanics are defined here. **No person is
bound to any role.** Binding a role to a real, accountable human is the owner's
decision (David P. Russell or delegate) and cannot be made by the build; every
role below therefore reads `UNASSIGNED`, which keeps the production gate NO_GO.

| Role | Accountable for | Holder | Backup |
|---|---|---|---|
| Service owner | tier existence, SLOs, roadmap | UNASSIGNED | UNASSIGNED |
| Code owner | `runtime.py`, `fvt/` review | UNASSIGNED | UNASSIGNED |
| Security owner | threat model, quarantine policy, key rotation | UNASSIGNED | UNASSIGNED |
| Operations owner | runbooks, on-call, backups | UNASSIGNED | UNASSIGNED |
| Release approver | production gate sign-off (must differ from builder) | UNASSIGNED | UNASSIGNED |

## Decision authority

| Action | Who may decide | Mechanism |
|---|---|---|
| Emergency disable (tier quarantine) | Security owner or on-call primary | `FullVmService.quarantine(token,"tier",reason)` — requires a human `admin` token; service tokens refused |
| Guest quarantine | on-call primary | `quarantine(token,"guest:<id>",reason)` |
| Config rollback | on-call primary; automatic on failed health check | `ConfigStore.rollback` |
| Risk acceptance / waiver | Service owner + Security owner | `governance/EXCEPTIONS.json` entry with expiry |
| Production release | Release approver | `evidence/PRODUCTION_APPROVAL.json` bound to artifact digest |

## Escalation intervals (proposed)

| Severity | Ack | Escalate to secondary | Escalate to service owner |
|---|---|---|---|
| SEV1 (isolation breach, primitive bypass) | 5 min | 10 min | 15 min |
| SEV2 (tier unavailable) | 15 min | 30 min | 60 min |
| SEV3 (degraded) | 4 h | next business day | weekly review |

A tabletop exercise of this path has **not** been run (blocker ELAPSED).
