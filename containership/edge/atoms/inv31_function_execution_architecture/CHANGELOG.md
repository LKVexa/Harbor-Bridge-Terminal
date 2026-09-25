# Changelog — INV-31

## 4.3.0 — 2026-09-22

Applied the 85-item remediation checklist. See `REMEDIATION_STATUS.json`.

- Added `boundary.py`, `errors.py`, `config.py`, `adapters.py`, `pkcompat.py`, schemas for
  request/error/config, fixtures, four example environment configs, docs, bench, evidence builder, CI.
- Package import no longer requires `pk_core` (was an uncontrolled ImportError).
- runtime.py: two semantics-preserving optimisations found by profiling (C065) — aged-eviction
  no longer builds a diagnostic dict per instance per invoke, and the reuse scan pre-filters on
  exact tenant/version before full revalidation. Burst workload (64 tenants, ~255 instances)
  p50 fell from ~376 µs to ~66 µs on the build host. Reuse rule unchanged; all 4.2.0 tests pass.
- Defect found by the new tests and fixed before delivery: an idempotent replay returned the
  bare pool record instead of the response envelope.
- Not done and not claimed: pk_core pin, Dandelion, MASTER.md, owner, licence, ADR approval,
  KMS/encryption, real adjacent-layer integration, fleet/edge measurements. Gate: NO_GO.

## 4.2.0 — 2026-09-22

Second audit, correctness hardening, evidence correction, and post-audit gap inventory.

### Runtime correctness and hardening

- Split the lifecycle engine into dependency-free `runtime.py` so safety behavior is independently testable when `pk_core` is unavailable.
- Replaced one shared scratch dictionary with per-invocation scratch scopes; completing one concurrent invocation no longer clears another invocation's state.
- Added lock protection around instance and pool state transitions.
- Made instance identity immutable after construction.
- Added validated, configurable concurrency, maximum-age, and pool-size limits.
- Added a hard pool safety ceiling with fail-closed `PoolCapacityExceeded` behavior when all capacity is busy.
- Added strict identifier and logical-time validation, including bounded identifier length and control-character rejection.
- Added fail-closed handling for clock rollback/negative instance age, including direct-entry `InstanceExpired` refusal.
- Added safe idle drain/quarantine via `destroy_idle()`.
- Added bounded pool diagnostics via `PK_FUNCTION_POOL/1`, including warm/cold counters and saturation signals without exposing scratch contents.
- Added stable warm/cold `decision_reason` values to `PK_INVOCATION/1`.

### Contract, evidence, and tests

- Corrected checklist-evidence misalignment in the component adapter: configuration validation now maps to C034, environment-specific runtime limits to C035, admission control to C054, isolation to C046, and safe drain/quarantine to C059.
- Removed the prior attempt to treat version-mismatch warm reuse as proof of executable-artifact signature/provenance verification (C045).
- Added versioned JSON Schemas for `PK_INVOCATION/1` and `PK_FUNCTION_POOL/1`.
- Added standalone tests for cold/warm reuse, tenant/version isolation, concurrent scratch isolation, threaded concurrency, clock rollback, bounded pool capacity, identity immutability, validation, diagnostics privacy, and safe drain behavior.
- Moved framework-dependent checks into a separate skipped class so absence of `pk_core` no longer causes every repository test to skip.
- Updated documentation to stop claiming that absent `MASTER.md` is bundled.

### Post-audit status

- Standalone test suite: passes under normal Python and `python -O`.
- Framework conformance: not executable from this archive because `pk_core` is absent.
- Remaining production gaps are enumerated in `MISSING_COMPONENTS.md` and `POST_AUDIT.json`.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

- Replaced bare behavioral `assert` checks with optimizer-safe verification.
- Added refusal-path `else` failures where expected exceptions back findings.
- Added a stdlib conformance test and version pin.
- Fixed unbalanced `leave()`, negative-age warm reuse, and empty tenant/version input.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
