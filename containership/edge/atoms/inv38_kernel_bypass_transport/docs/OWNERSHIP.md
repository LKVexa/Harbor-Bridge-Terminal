# INV-38 Ownership & Escalation (C009)

**Accountable service owner:** platform-transport-team (role: Staff Engineer, TZ coverage: follow-the-sun via 3 regions). **Backup owner:** platform-dataplane-team. **Effective:** 2026-09-22.

## On-call
Production paging routes through `ops/escalation.yaml` (`destination_ref`) — a
secrets-less reference resolved by the org paging integration. No personal phone
numbers or secrets live in the repository.

## RACI (C009-T03)
| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Architecture approval | transport-team | architecture-board | security-team | stakeholders |
| RDMA/provider qualification | platform-team | transport-owner | vendor | ops |
| Security review | security-team | security-architecture-board | transport-team | ops |
| Release approval | transport-owner | architecture-board | security-team | stakeholders |
| Incident command | on-call IC | transport-owner | security-team | leadership |
| End-of-life decision | architecture-board | product-owner | transport-team | customers |

## Escalation & handoff
Severity timers and cross-component handoff (INV-35/36/37/GAP-12) are defined in
`ops/escalation.yaml`. Ownership changes are transferred via PR to
`docs/OWNERSHIP.md` + `.github/CODEOWNERS` under security review, so stale
mappings cannot silently persist (C009-T08).

## Status against C009
`IN_PROGRESS` — artifact present; the non-production escalation drill (C009-T07)
requires a live paging integration and is not reproducible from this archive.
