# INV-35 4.3.0 production-exit summary (generated — do not edit)

* Verdict: **PARTIAL**
* Tree digest: `f233703edfd90a469c60e606eb339879d82c70eb050ea0647b711f6ba9988b6e`
* Generated: 2026-09-23T03:26:21.171234+00:00
* Evidence sealed: False
* Audit rows: {'present': 8, 'partial': 91, 'missing': 1}
* Work packages: {'implemented_pending': 102, 'open': 1}

## Gates

| Gate | OK |
|---|---|
| G1_compile | yes |
| G2_schemas | yes |
| G3_tests | yes |
| G4_rtm | yes |
| G5_performance | yes |
| G6_supply_chain | yes |
| G7_ownership | no |
| G8_license | no |
| G9_approvals | no |
| G10_waivers_reviews | no |
| G11_dependencies | no |
| G12_sealed | no |

## Blockers

- [tests] 3 mandatory test(s) skipped
- [pk_core] pk_core not importable: set PK_CORE_PATH or install the approved pinned pk_core
- [ownership] role accountable_owner not accepted by David Paul Russell
- [ownership] role code_owner unassigned
- [ownership] role security_owner unassigned
- [ownership] role runtime_platform_owner unassigned
- [ownership] role operations_owner unassigned
- [license] repository license not selected/approved
- [approval] docs/adr/ADR-0001-separate-orchestration-and-bulk-data-channels.md awaiting accountable_owner
- [approval] docs/adr/ADR-0001-separate-orchestration-and-bulk-data-channels.md awaiting security_owner
- [approval] docs/architecture/ARCHITECTURE.md awaiting accountable_owner
- [approval] docs/requirements/INV-35_REQUIREMENTS.md awaiting accountable_owner
- [approval] docs/security/THREAT_MODEL.md awaiting accountable_owner
- [approval] docs/security/THREAT_MODEL.md awaiting security_owner
- [approval] docs/resilience/FMEA.md awaiting accountable_owner
- [approval] docs/operations/SLO.md awaiting accountable_owner
- [approval] docs/operations/ROLLOUT_AND_ROLLBACK.md awaiting accountable_owner
- [approval] docs/operations/INCIDENT_RESPONSE.md awaiting accountable_owner
- [approval] runbooks/RUNBOOKS.md awaiting accountable_owner
- [approval] governance/OWNERS.json awaiting accountable_owner
- [approval] CLOSURE_LEDGER.json (row-level acceptance of implemented evidence) awaiting accountable_owner
- [approval] CLOSURE_LEDGER.json (repository packages) awaiting accountable_owner
- [waiver] waiver WVR-001 not approved
- [waiver] waiver WVR-002 not approved
- [waiver] waiver WVR-003 not approved
- [dependency] pk_core not pinned (unpinned-unavailable)
- [rollout] canary/rollback drill evidence evidence/rollout-4.3.0.json absent (G13)
- [seal] INV35_EVIDENCE_KEY not provided
