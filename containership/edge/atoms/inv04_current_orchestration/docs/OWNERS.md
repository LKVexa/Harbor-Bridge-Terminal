# INV-04 Ownership, RACI and Escalation (component 75)

- **Status:** Template only. **Every role below is UNASSIGNED.**

Component #75 and checklist items C009, C097 and C098 stay open until the owner fills in named people and routes. Names have not been invented.

| Role | Person / team | Contact / route | Responsibility |
|---|---|---|---|
| Accountable owner | UNASSIGNED | — | Go/no-go, waivers, ADR approval |
| Engineering lead | UNASSIGNED | — | Code, reviews, releases |
| On-call primary | UNASSIGNED | page route `inv04-oncall` (to be created) | Pages from `evaluate_alerts` |
| Security contact | UNASSIGNED | — | Threat-model review, vulnerability response |
| Dependency owner: Kubernetes adapter / API server | UNASSIGNED | — | Component #1, #58 |
| Dependency owner: SCH-01 successor scheduler | UNASSIGNED | — | Hand-off #37–#39, parity #59 |
| Dependency owner: pk_core | UNASSIGNED | — | Component #78 |
| Change approvers (config, policy, release) | UNASSIGNED | — | `ConfigManager.apply` issuers; release sign-off |

## RACI

| Activity | Owner | Eng lead | On-call | Security |
|---|---|---|---|---|
| Release go/no-go | A | R | C | C |
| Drain policy / PDB exceptions | A | R | I | C |
| Incident response | I | C | R/A | C |
| Threat-model review (recurring) | A | C | I | R |
| Access and dependency review (C098) | A | R | I | R |

## Escalation

On-call primary → engineering lead (15 min) → accountable owner (30 min). Security incidents go straight to the security contact. Fill in the timings once people are assigned.
