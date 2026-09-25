# GAP-11 ownership and escalation (GAP11-P2-46)

**Status:** BLOCKED — no accountable owner has been named.

| Role | Assigned | Required before |
|---|---|---|
| Accountable owner | UNASSIGNED | GAP11-EXIT-01 |
| Security approver (threat model, exceptions) | UNASSIGNED | GAP11-EXIT-05 |
| Release approver | UNASSIGNED | GAP11-EXIT-07 |
| On-call rotation / escalation route | UNASSIGNED | GAP11-EXIT-08 |

Proposed severity policy (for the owner to accept or replace): SEV-1 any evidence of cross-tenant exposure, double allocation, or audit-verify failure → page, freeze mutations (`Controller.freeze(True)`), preserve store and ledger; SEV-2 scrub failures above alert threshold or leader flapping; SEV-3 capacity refusals above threshold.

This file intentionally names nobody. The build refuses to invent an owner; the exit bundle stays NO_GO until this table is filled by a human and approved.
