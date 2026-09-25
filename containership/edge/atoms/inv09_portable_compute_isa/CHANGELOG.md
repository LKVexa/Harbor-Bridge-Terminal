# Changelog - INV-09

## 4.3.0 - 2026-09-22

Execution of the *INV-09 v4.2.0 Missing-Components Production Checklist* (52 components, 2,704 items).

### Added
- `prod/`: byte-level validation boundary (M01-M13), host-import contract + WASI adapter (M17/M18), signed
  policy bundles (M22), audit/metrics/logs/traces/explain (M27, M33-M37), benchmark + perf gate (M29/M30),
  canary controller (M39), config provenance/activation/reconstruction (M42-M44), waivers (M51), production
  gate (M52), fuzzing (M14) and V8 differential harness (M15).
- `schemas/` (9 JSON Schemas), `docs/` (design, threat model, determinism, operations, integration, 6 ADRs),
  `ops/` alert rules and dashboard, `pyproject.toml`, `requirements.lock`, `OWNERS.yaml` (to be filled).
- Tests: 80+ unit/integration/fault/gate tests; hand corpus judged against V8; 200k-input fuzz campaign.
- `CHECKLIST_STATUS.{md,json}`, `TRACEABILITY.json`, `evidence/*.json` bound to the release digest.

### Changed
- Profiles now include the Wasm 2.0 standard features `mutable-globals-import`, `sign-ext`,
  `sat-float-to-int` (kernel and bundle kept equal by test).
- `__init__` tolerates a missing `pk_core` (the prod boundary does not need it); conformance tests still skip.

### Fixed during the pass
- See `FINDINGS.md` (F-01..F-05), including cache-poisoning to accept (F-01) and a governor deadline that
  never fired on small inputs (F-04).

### Known gaps (production gate NO_GO)
- Latency SLO not met by the pure-Python validator (F-07 / ADR-0006); owners unnamed (M50); one
  differential reference only; no certified engines / multi-arch determinism; component model (M19) absent.

## 4.2.0 - 2026-09-22

Audit, parse, fix, and hardening pass.

### Security and correctness

- Split the security-critical validation policy into dependency-light `validator.py` so it can be tested without `pk_core`.
- Fail closed when a module merely **declares** a capability outside the selected profile; v4.1.0 reported it in `declared_unsupported` while still returning `valid=True`.
- Reject unknown/unregistered feature names instead of silently accepting unknown declared capabilities.
- Validate profile type before lookup so unhashable inputs cannot surface accidental `TypeError` paths.
- Validate module names, feature-name syntax, feature counts, `well_formed` type, section count, and byte-size metadata before policy arithmetic.
- Snapshot mutable feature sets before evaluation to reduce time-of-check/time-of-use ambiguity.
- Bound module-name and feature metadata used in diagnostics and policy processing.
- Preserve `python -O` behaviour by keeping behavioural gates independent of bare `assert`.

### Verification

- Added standalone validator tests that run even when the external `pk_core` harness is unavailable.
- Added regression coverage for declared-but-unsupported features, unknown features, malformed scalar types, unhashable profiles, name/control-character handling, feature-count limits, deterministic output, and nondeterministic permissive-profile reporting.
- The 100-requirement `pk_core` conformance suite remains dependency-gated and cannot execute in an environment where `pk_core` is absent; this is recorded in `AUDIT_REPORT.md`.

### Documentation

- Clarified that the current implementation is a descriptor-level policy kernel, not yet a production Wasm binary decoder/type validator.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md` with production-readiness gaps and priorities.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::validate: mandatory "detect declared-but-unsupported features" was not implemented (declared features outside the profile were silently lumped into declared_unused) -> report them in a new "declared_unsupported" result field
- component.py::validate: negative/non-int sections or size_bytes passed the limit checks, and non-set feature fields crashed with TypeError on set arithmetic -> refuse with ValidationFailed

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
