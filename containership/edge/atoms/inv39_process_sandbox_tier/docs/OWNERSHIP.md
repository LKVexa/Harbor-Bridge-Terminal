# Ownership and escalation (MC-001)

**Status: BLOCKED — requires a named human.** Nothing in this repository can appoint an owner; this file defines the slots and the escalation path so the owner decision is a fill-in, not a design task.

| Role | Name | Contact | Backup | Accepted on |
|---|---|---|---|---|
| Accountable owner (INV-39) | _UNASSIGNED_ | | | |
| Security reviewer (independent of the implementer) | _UNASSIGNED_ | | | |
| Operations on-call rotation | _UNASSIGNED_ | | | |
| Release approver | _UNASSIGNED_ | | | |

Escalation path: on-call → accountable owner (30 min, SEV1/SEV2) → security reviewer for any suspected escape (immediately, parallel) → platform leadership (SEV1 not contained in 2 h).

The exit gate (`tools/exit_gate.py`) reads this table; any `_UNASSIGNED_` role is a NO_GO reason.
