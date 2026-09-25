# Changelog — INV-68

## 4.3.0 — 2026-09-23

Missing-component implementation pass driven by
`INV68_v4.2.0_Missing_Component_Implementation_Checklists.md` (MC-01..MC-42, 1,844 items).

### Defects fixed (found by this pass's own checks)
- **Performance SLO violation:** 4.2.0 packed 1000 workloads in ~311 ms p50 (SLO p99 < 100 ms) and
  5000 one-per-host workloads in ~51 s. Validation now happens once and full hosts leave the scan;
  decisions are byte-identical (differential test + fuzz oracle). Now ~6 ms / ~45 ms.
- **`lower_bound` raised `OverflowError`** for extreme-but-finite inputs, escaping the documented
  `TypeError`/`ValueError` contract (fuzz finding). Now `ValueError`.
- **`lower_bound` counted unplaceable workloads**, overstating the bound whenever anything was
  unplaced. Default kept for compatibility; `placeable_only=True` added and used by service/bench.
- Service-level: out-of-range JSON numbers (`1e999`) and non-JSON values produced an internal error
  (fuzz finding) — now `INVALID_REQUEST`.

### Added
- `service.py` boundary; `auth.py` (tokens, capability ceilings, tenant scope, replay protection);
  `config.py` (`PK_PACK_CONFIG/1`, overlays, CAS + epoch + inter-process lock, crash recovery,
  rollback, diff, backup/restore); `errors.py` (registry, `ERRORS.json`); `resilience.py`
  (admission, shedding, breaker, deadlines, backoff); `telemetry.py`; `explain.py`; `audit.py`,
  `redaction.py`, `provenance.py`, `release_gate.py` (adapted from the owner's INV-64 4.3.0);
  `rollout.py`; `adjacent.py` emulators for INV-67, SCH-01, GAP-10, INV-72.
- Engine: configurable `cpu_overcommit` in [1, 4] (memory fixed at 1.0).
- Six new JSON schemas; examples for config and service requests.
- Tools: run_evidence, bench (+ baseline/regression gate), fuzz, faults (14), stress/soak (7 races incl.
  cross-process), drills, integration, schemas_check, secret_scan, source_integrity, preflight,
  bootstrap.sh/.ps1, slo_report, governance_check, release (wheel/sdist/SBOM/DSSE/install-check), build_ledger.
- Docs: SPECIFICATION, INTERFACES, SECURITY, THREAT_MODEL, FAILURE_MODEL, CONFIGURATION, BENCHMARKS,
  TELEMETRY_POLICY, RUNBOOK, INCIDENT_RESPONSE, SECURITY_RESPONSE, BACKUP_RESTORE, COMPATIBILITY,
  GOVERNANCE, REQUIREMENTS_TRACEABILITY, LICENSING, NOTICE, THIRD-PARTY-NOTICES; ops/ metadata; CI workflow.

### Not done (honest)
- Exit gate verdict **NO_GO**; see AUDIT_REPORT.md §4.3.0 for every blocker and what closes it.


## 4.2.0 — 2026-09-22

Second audit, parsing, hardening, and version-bump pass.

### Core-engine hardening

- Extracted the packing algorithm into dependency-free `packing.py`; importing
  and testing core functionality no longer requires the external `pk_core` framework.
- Added lazy loading for `pk_core` control-plane integration with a precise error
  if the framework is unavailable.
- Replaced caller-input mutation (`workload["host"] = ...`) with copied/normalized
  inputs and an explicit immutable assignment map in `PackingResult`.
- Added strict finite-number validation for host capacity, headroom, workload CPU,
  workload memory, and host accounting. Booleans are rejected as resource numbers.
- Added structural workload validation, non-empty names, and duplicate-name rejection.
- Made first-fit-decreasing ordering deterministic for equal dominant shares.
- Unified placement ordering and lower-bound math around effective capacity after
  overcommit and headroom policy.
- Added host-accounting invariant checks to `fragmentation()` so impossible
  negative stranded capacity fails closed instead of being reported as valid.
- Added `pack_detailed()`, `PackingResult`, and `PlacementDecision` for explicit,
  machine-readable placement and refusal reasons.

### Interface and test hardening

- Added versioned JSON Schema 2020-12 contracts for `PK_PACK/1`,
  `PK_PACK_CAPACITY/1`, and `PK_PACK_FRAG/1`.
- Added request/response conformance examples.
- Added a standalone unit/hardening suite covering malformed and adversarial
  numeric inputs, no-mutation behavior, deterministic ordering, headroom,
  memory-overcommit prevention, fragmentation invariants, schemas, and `python -O`.
- Reworked framework tests so package/version checks still execute when `pk_core`
  is absent; only the two actual framework-dependent checks skip.

### Documentation and audit integrity

- Corrected the README's false statement that `MASTER.md` was present.
- Added `AUDIT_REPORT.md`, `POST_UPDATE_AUDIT.md`, and `MISSING_COMPONENTS.md`.
- Version bumped from 4.1.0 to 4.2.0 in `VERSION`, `__version__`, tests, and docs.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess
  bands replaced by `_verify()` so behavioural checks still run under `python -O`.
- `component.py`: refusal-backed findings changed to fail if the expected refusal
  does not occur instead of silently keeping a contract-derived default finding.
- `tests/test_component.py`: stdlib conformance test for 100 findings, optimized
  mode parity, and version pin.
- `VERSION` and `__version__` added.

### Defects fixed

- `pack`/`lower_bound`: reject zero/negative host capacity, invalid headroom, and
  negative workload requests.

### Gate claim in 4.1.0

The 4.1.0 changelog stated that all 100 requirements were satisfied. The 4.2.0
re-audit cannot independently reproduce that claim from this isolated archive
because `pk_core` is not included, and many production checklist requirements
lack concrete repository-local implementation/evidence. See `POST_UPDATE_AUDIT.md`.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
