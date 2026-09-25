# INV-24 ownership and escalation (MC-007)

| Role | Holder | Status |
|---|---|---|
| Accountable owner (package) | **UNASSIGNED** | BLOCKED — must be named and accept in writing |
| Technical reviewer / approver | **UNASSIGNED** | BLOCKED |
| Security approver | **UNASSIGNED** | BLOCKED |
| On-call rotation (primary/secondary) | **UNASSIGNED** | BLOCKED — needs paging system binding |
| Release manager | **UNASSIGNED** | BLOCKED |

This pass deliberately does not invent people. `release/COMPONENT_STATUS.json`
lists `owner: null` for every component and the production gate
(`tools/production_gate.py`) fails any P0 component without an owner.

## Escalation path (to be bound to names)
1. On-call primary (page, 5 min ack for SEV1/SEV2 — see `INCIDENT_RESPONSE.md`)
2. On-call secondary (15 min)
3. Accountable owner (30 min)
4. Security approver — mandatory for any suspected escape, key or audit-chain event

Machine-readable form: `CODEOWNERS` at the repository root.
