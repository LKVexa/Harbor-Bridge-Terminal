# Ownership, escalation and authority (C009, C097, A6)

> **Status: STRUCTURE ONLY — every role below is UNASSIGNED.** Binding named, accountable people or teams
> is an organisational decision that this repository cannot make. Until each role is bound, C009 and C097
> stay open and no production certification can be signed (the release gate refuses an empty approver).

## Roles

| Role | Accountable for | Team alias (placeholder) | Bound to |
|---|---|---|---|
| Engineering owner | code, ADRs, RTM, releases | `inv45-eng@<org>` | UNASSIGNED |
| Security owner | threat model, residual risks, key compromise, SEV-0/1 | `inv45-security@<org>` | UNASSIGNED |
| Operations owner | SLOs, runbooks, on-call, dashboards | `inv45-ops@<org>` | UNASSIGNED |
| Performance owner | thresholds.json approval, perf gate waivers | `inv45-perf@<org>` | UNASSIGNED |
| Release approver | production exit gate (C100) signature | `inv45-release@<org>` | UNASSIGNED |

## On-call

Primary and secondary rotations on the operations alias, 24×7 for SEV-0/1, business hours otherwise; weekly
handoff with an open-incident review. **No rotation exists yet.**

## RACI

| Activity | Eng | Sec | Ops | Perf | Release |
|---|---|---|---|---|---|
| Architecture approval (ADR) | R | A | C | C | I |
| Policy change (profile/config base) | R | A | C | I | I |
| Production deployment | C | I | R/A | I | C |
| Security incident response | C | A | R | I | I |
| Emergency disable (global = two humans) | I | A | R | I | I |
| Rollback | C | I | R/A | I | I |
| Release certification (C100) | R | C | C | C | A |
| Performance threshold approval | C | I | I | A | I |

## Emergency authority

Tenant/artifact quarantine: any holder of `sfi.quarantine`. Global disable/release and key revocation: two
distinct **human** principals holding `sfi.quarantine` / `sfi.keys.admin` (enforced in code for quarantine;
procedural for key revocation).

## Review triggers

Re-confirm this file on: organisational change, any expired or unreachable alias, a new adjacent-layer
dependency, a component reaching EOL, or quarterly — whichever is first.
