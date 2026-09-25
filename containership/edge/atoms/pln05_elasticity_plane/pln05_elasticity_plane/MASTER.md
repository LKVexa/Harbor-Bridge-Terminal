# PLN-05 master workflow (authoritative source, version 4.2.0)

This file replaces the absent `MASTER.md` that 4.1.0 referenced (MC-32). It is the repository's authoritative **remediation / release workflow**; it references requirements and gates by ID and never restates their text. Scope follows `docs/adr/ADR-0001-pln05-authoritative-scope.md`. The input for the 4.2.0 pass is kept verbatim in `source/PLN05_v4.1.1_Missing_Component_Remediation_Checklists.md` (sha256 recorded in `source/SOURCE.json`).

| Phase | Input | Output | Automatable check | Human approval |
|---|---|---|---|---|
| P0 scope lock | ADR-0001, `spec.py` | `spec/pln05_scope.json` | `tools/check_repo.py` scope drift | architecture owner (ADR) |
| P1 requirements | CHECKLIST.json C001–C100, `spec/pln05_nfr.json` | `traceability/requirements.json` | `tools/traceability.py --check` | service owner |
| P2 interfaces | `schemas/*.json` | fixtures, `tests/contract` | `tools/schema_compat.py`, contract tests | — |
| P3 implementation | runtime modules | tests | `tools/ci.py` unit/plane tiers (normal and `-O`) | technical owner review |
| P4 security | `security/*` | adversarial suite | `tests/security` (T01–T20 mapping check) | security contact |
| P5 resilience | `ops/reliability/*` | fault results | `tests/fault` | — |
| P6 performance | `benchmarks/*` | bench results | `ci/performance_gate.py` | release approver approves baseline |
| P7 operations | runbooks, alerts, dashboards | alert tests | `tests/test_ops.py` | operations owner |
| P8 evidence | all of the above | `evidence/4.2.0/manifest.json` | `tools/ci.py --release` | — |
| P9 exit gate | evidence bundle, `governance/*` | `evidence/4.2.0/EXIT_GATE.json` | `tools/gate.py` | release approver + service owner sign `governance/approvals.json` |

Commands (Linux/macOS; on Windows use `py -3` for `python3`):

```
python3 tools/ci.py                 # presubmit tier, writes evidence/<version>/
python3 tools/ci.py --release       # release tier: fails on any skip, builds wheel/sdist/SBOM/provenance
python3 tools/gate.py               # production exit gate over the evidence bundle
```

Rules: no step may claim a pass without a machine-readable result in the evidence bundle; skipped mandatory checks are failures in the release tier; the tool that produced evidence may not approve it.

Change history: 4.2.0 — created (ADR-0001, remediation of MC-01..MC-34).
