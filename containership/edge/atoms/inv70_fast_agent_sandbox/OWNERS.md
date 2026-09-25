# INV-70 Fast agent sandbox — ownership and escalation (INV-70-C009)

| Role | Holder | Responsibility |
|---|---|---|
| Accountable owner | **David Paul Russell** (davidpaulrussell@linearfinance.org) | Final say on scope, ADRs, releases, waivers |
| On-call alias | **UNASSIGNED** — owner must name | First responder for SEV1–SEV3 pages (RUNBOOK.md) |
| Security reviewer | **UNASSIGNED** — owner must name | Required approver for `security.py`, `executor.py`, `runtime.py`, ADRs |
| Reliability reviewer | **UNASSIGNED** — owner must name | Required approver for `resilience.py`, `config.py`, perf gate changes |

## Escalation path

1. On-call alias (page; ack within 15 min for SEV1/SEV2).
2. Accountable owner (if no ack in 30 min, or any containment that disables a tenant).
3. Security reviewer for any `FB-S0xx` spike, audit-chain failure (`FB-S022`) or suspected escape.

## Review rules

- Changes touching the files above need the named specialist's approval in addition to the owner.
- While a role is UNASSIGNED the owner holds it; this is recorded as an open item in `EXCEPTIONS.yaml` (EXC-001).
