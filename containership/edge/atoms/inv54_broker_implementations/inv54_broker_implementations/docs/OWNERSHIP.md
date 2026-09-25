# INV-54 ownership and escalation  (REQ-GOV-001 · controls INV-54-C009)

| Field | Value | Status |
|---|---|---|
| Accountable owner | David Paul Russell (davidpaulrussell@linearfinance.org) | stated by package owner |
| Backup owner | **UNASSIGNED** | open item OWN-2 — blocks C009 PASS |
| Paging target / on-call alias | **UNASSIGNED** | open item OWN-3 — no paging system named |
| Decision authority: contract/interface changes | accountable owner + INV-52 owner | INV-52 owner unknown (OWN-4) |
| Decision authority: security policy, secret handling, release sign-off | accountable owner | — |
| Document version | 1.0 (INV-54 4.3.0) · next review: on any ownership change or 90 days | — |

## Escalation levels (normative)

1. **L1 – on-call** (UNASSIGNED): acknowledge within the SLO in `SLO.md`; may drain, quarantine, roll back config.
2. **L2 – accountable owner**: approves waivers, provider enable/disable, emergency release.
3. **L3 – upstream owners**: INV-52 (contract), INV-53 (delivery guarantees) for semantic disputes; INV-49 for admission of adapters.

## Ownership boundaries

- INV-54 **owns**: reference brokers, production layer in this package, provider adapters' *mapping* code, conformance suite.
- INV-54 **does not own**: the messaging contract (INV-52), delivery-guarantee policy (INV-53), operating provider clusters, schemas of payloads, transport infrastructure. Adapters MUST NOT redefine INV-52/53 semantics; divergence is reported as `UNSUPPORTED_FEATURE`, never silently emulated.
- Downstream INV-49 admits adapters by running `adapters.run_conformance`.

## Automated check

`tools/check_owners.py` walks every tracked file and fails if one is not covered by `CODEOWNERS`
(test `test_c01_every_path_owned`).
