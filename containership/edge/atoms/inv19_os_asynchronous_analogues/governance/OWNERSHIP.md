# INV-19 Ownership and Escalation (C009, MC-28)

| Role | Holder | Status |
|---|---|---|
| Accountable component owner / team | **UNASSIGNED** | BLOCKED — the owner must name a person or team; this file may not invent one |
| Operational owner (on-call) | **UNASSIGNED** | BLOCKED |
| Security escalation path | **UNASSIGNED** (route: operational owner → security on-call → accountable owner) | BLOCKED until names exist |
| Release approver role | "INV-19 release approver" (role defined; holder UNASSIGNED) | BLOCKED |
| Contact / paging mechanism | Paging target to be bound to the alert rules in `hostio/observability.py::ALERT_RULES` | BLOCKED |

## Ownership transfer process
1. Outgoing owner opens a transfer record in `EXCEPTIONS.md` style (who, when, why).
2. Incoming owner re-runs `python tools/run_gate.py` and signs the resulting gate digest.
3. Both names are recorded here; the release approver countersigns.
4. The gate refuses GO while any row above is UNASSIGNED (check C009).
