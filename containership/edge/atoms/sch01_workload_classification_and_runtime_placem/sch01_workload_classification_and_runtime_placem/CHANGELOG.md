# Changelog - SCH-01

## 4.3.0 — 2026-09-23

- Governed placement service (`scheduler.py`) implementing MC-07..MC-41 mechanisms, plus schemas, error catalog v2, durable fenced journal, audit ledger, telemetry, canary, exit gate, RTM, SBOM, CI.
- `engine.py` v1 API unchanged. `PK_PLACEMENT/1` and `PK_SCHEDULER_ERROR/1` are deprecated.
- Exit gate NO_GO. See EXECUTION_REPORT_4.3.0.md.

## 4.2.0 - 2026-09-22

Second audit, hardening, and independent-verification pass.

### Runtime hardening

- Split dependency-independent scheduler logic into `engine.py`; package import and core tests no longer require `pk_core`.
- Added strict workload/node/time/lease validation and rejection of unsupported isolation tiers.
- Revalidate mutable `NodeReport` state at decision boundaries so post-construction mutation cannot bypass validation.
- Added canonical-classification verification so a caller-supplied classification cannot downgrade a workload.
- Reject future-dated node reports in addition to stale reports.
- Fail closed on cross-tenant co-location because the current occupancy model lacks enough tier/trust metadata to prove safe sharing.
- Reject duplicate node identities and preserve duplicate-workload lease protection.
- Added a process-local placement lock covering selection and mutation to prevent in-process slot oversubscription.
- Added structured `PK_SCHEDULER_ERROR/1` refusals with stable codes and aggregate rejection counts.
- Added `lease_issued_at`, total-candidate count, and deterministic decision metadata to placement results.
- Enabled the previously unreachable `first-party` -> `wasm` classification path.
- Corrected `WorkloadClassificationAndRuntimePlacemenComponent` to `WorkloadClassificationAndRuntimePlacementComponent` while retaining the old spelling as a compatibility alias.

### Verification and documentation

- Added 15 dependency-independent scheduler tests, including a two-thread one-slot oversubscription test and an optimized-mode smoke test.
- Kept pk_core integration tests explicit and skipped only when the external dependency is unavailable; version validation now runs regardless.
- Corrected the README's false `MASTER.md` inventory statement instead of fabricating missing source evidence.
- Added `ARCHITECTURE.md`, `SCHEMAS.md`, `SECURITY.md`, `OPERATIONS.md`, `AUDIT_REPORT.md`, and `MISSING_COMPONENTS.md`.
- Version bumped from 4.1.0 to 4.2.0.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::classify: unknown provenance crashed with KeyError -> Unplaceable naming the provenance
- component.py::place: the same workload could be placed twice (two leases, two slots), contradicting "exactly one placement lease" -> Unplaceable if already an occupant
- component.py::place: non-positive lease_ticks (lease already expired) and empty name/tenant accepted -> ValueError
- component.py::NodeReport.occupants: comment said values are trust classes but place/candidates store and compare tenants -> comment corrected

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
