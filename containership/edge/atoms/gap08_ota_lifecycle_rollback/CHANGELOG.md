# Changelog - GAP-08

## 4.3.0 - 2026-09-22

Executed the GAP-08 v4.2.0 Missing-Components Professional Checklist (junkyard chop-shop pass).

### Added (one module per checklist component)
- P0: durable CAS/fenced state store with backup/restore (`store.py`), lease + fencing tokens (`lease.py`), cross-rollout conflict detector (`conflicts.py`), authenticated health-gate adapter (`health.py`), externally sealed WORM audit sink with reconstruction (`audit_sink.py`), GAP-07 digest/content verifier (`artifact.py`), A/B transactional installer with power-loss hooks (`installer.py`), authenticated command executor (`executor.py`), blast-radius engine (`topology.py`), emergency freeze (`freeze.py`), capability + environment-scoped authorization with two-person approvals (`authz.py`), device identity/attestation (`identity.py`), persistent deferred scheduler (`deferred.py`), idempotent fenced transport with rollback tombstones (`transport.py`), fail-closed dependency policy (`dependencies.py`).
- P1: retry/backoff/jitter + circuit breaker (`retry.py`), admission control with reserved recovery lane (`admission.py`), maintenance windows (`windows.py`), resumable verified chunk distribution (`distribution.py`), 14 JSON Schemas + validator (`schemas/`, `schema.py`), `PK_ERROR/1` taxonomy (`errors.py`), telemetry exporter + alert rules (`telemetry.py`), explain view (`explain.py`), compatibility matrix (`compat.py`), signed configuration provenance (`config.py`), secrets boundary (`secrets_boundary.py`), cancellation / quarantine recovery / reconciliation / takeover in `controller.py`.
- P2: seeded property/fuzz suite, concurrency + chaos campaign, fault-injection harness, benchmark, soak driver, simulated power-loss certification, release evidence bundle + SBOM, ADR-0001, owners/escalation template, threat model, runbooks, integration contracts, checklist status generator (1,286 items).

### Fixed (found by the new harnesses)
- Race: an operator rollback (or failed-gate rollback) sent node commands *before* winning the state CAS; a concurrent gate could commit first, leaving nodes on v1 while the record said v2. Rollback is now two-phase (CAS-committed intent → commands → outcome) and resumable by `recover()`.
- Race: a delayed install from a dispatch could land after a concurrent rollback. Nodes now tombstone a rollout when they execute its rollback and reject later installs for it (GAP-01 contract).
- Concurrent operations inside one controller could both re-acquire a lapsed lease and fence each other; lease handling is now serialized per controller.
- `retry_deferred` returned early before authorization when nothing was due; authorization now happens first.
- `import gap08_ota_lifecycle_rollback` failed without `pk_core`; the framework binding is now imported lazily.

### Changed
- Version 4.3.0. `contract.py` owns/interfaces/dependencies updated for the new surfaces.

## 4.2.0 - 2026-09-22

Audit, parse, fix, harden, and version-bump pass.

### Runtime and state-machine fixes

- Extracted the safety-critical rollout state machine into dependency-light `rollout.py` so it can be validated without `pk_core`.
- Reject empty waves, duplicate nodes within/across waves, and shrinking wave sizes before rollout starts.
- Require upstream verification to be bound to the exact bundle identifier; a bare `verified: true` verdict no longer admits an artifact.
- Reject unsupported verification schemas and malformed optional SHA-256 digests.
- Require explicit boolean health verdicts and reject offline-node reports that are outside the active wave.
- Added a `deferred` lifecycle state: a rollout with offline nodes cannot report full completion.
- Added separately gated deferred-node catch-up.
- Added incomplete-rollback reporting and quarantine for nodes that fail rollback.
- Added crash/restart snapshots with whole-state digests and restore-time invariant validation.
- Added chained transition-integrity records and chain verification.
- Reject non-finite or non-JSON-serializable gate evidence.

### Verification and evidence fixes

- Added 11 standalone safety tests covering topology, pinning, bundle binding, gate input validation, rollback containment, deferred catch-up, rollback failure quarantine, snapshot recovery, and tamper detection.
- Corrected framework assessment overrides so behavioral evidence is attached to requirements it actually demonstrates instead of unrelated checklist slots.
- Kept optimized-mode (`python -O`) behavioral checks independent of bare `assert` statements in production assessment code.

### Documentation and audit corrections

- Removed the stale README claim that a `MASTER.md` file is present; it was not included in the archive.
- Documented the new state, audit, deferred-retry, and rollback-failure semantics.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md` with remaining production gaps and external dependencies.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Rollout.admit: any dict with a truthy "verified" admitted the bundle, including a verification of a different artifact kind (e.g. a label or grant) -> require verified is True and kind == "bundle" (GAP-07 PK_VERIFICATION shape); assess_* updated to pass the kind
- component.py::Rollout.pin: waves could name nodes outside the pinned fleet (they were then "rolled back" to a version they never ran), and a bundle equal to the current version produced a no-op rollback target -> ValueError / NoRollbackTarget at pin time
- component.py::Rollout.run_wave: a node offline in several waves was appended to `deferred` repeatedly -> dedupe

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
