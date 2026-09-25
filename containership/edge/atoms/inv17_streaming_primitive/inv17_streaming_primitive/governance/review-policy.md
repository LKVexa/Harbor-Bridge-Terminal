# INV-17 Governance Review Policy

**Controls:** C098 (checklist §59); inputs C009/C097 (§1), C099-area registers (§60).

**Status:** Proposed. Owner: UNASSIGNED — owner to fill (see governance/OWNERS.json).

## 1. Cadence (PROPOSED)

| Review | Frequency | Trigger also on |
|--------|-----------|-----------------|
| Governance review | Quarterly | major/minor release, Sev0/Sev1 incident |
| Waiver / technical-debt review | Monthly | any waiver nearing expiry |
| ADR review | On change to `stream.py` semantics or error precedence | – |
| Threat-model review | Semi-annually | new trust dependency |

## 2. Inputs

- `governance/OWNERS.json`, `governance/waivers.json`, `governance/technical-debt.json`
- `conformance/PRODUCTION_EXIT_GATE.json` and output of `tools/exit_gate.py`
- `tools/validate_governance.py` result (schema + expiry checks)
- `tools/gen_traceability.py` (REQ ↔ code ↔ tests)
- Incident records since last review; audit ledger exports

## 3. Checklist per review

1. Every owner/approver field is filled with a real, reachable person (currently all placeholders — blocker).
2. No expired waiver; each waiver has owner, expiry, compensating control.
3. ADRs: status recorded; none left "Proposed" past one cycle without decision.
4. Exit-gate items: evidence present, not asserted. Unmeasured items (e.g. power/thermal, fleet scale) remain explicitly marked unmeasured.
5. Runbook and escalation contacts reviewed.

## 4. Records

Each review produces a dated record (location to be chosen by owner) listing attendees, decisions, and actions with owners. No review has been held yet.
