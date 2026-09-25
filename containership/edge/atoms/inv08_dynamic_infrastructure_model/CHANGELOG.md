# Changelog - INV-08

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening, and evidence-quality pass.

### Correctness and state-safety fixes

- Reject non-finite (`NaN`, `+/-Inf`), negative, and boolean demand values.
- Reject non-finite or boolean time inputs and reject backward time movement.
- Validate restored/external node state before every decision; malformed lease
  records now fail closed with `PoolInvariantError`.
- Make `Pool.tick()` transactional by calculating against a copy and committing
  only after all validation and arithmetic succeeds.
- Prevent generated node-ID collisions after state restore/import.
- Reject boolean bounds (`True`/`False`), which Python otherwise treats as ints.
- Detect non-finite lease-expiry and node-hour arithmetic.
- Add explicit `elapsed_hours` to make node-hour accounting semantics testable.

### Architecture and test hardening

- Extracted the dependency-free pool engine to `model.py`.
- Added `metadata.py` so identity/version/model tests do not require `pk_core`.
- Changed package adapter loading to lazy imports; the reference model can now be
  tested even when the external conformance framework is absent.
- Split always-on standalone model tests from `pk_core` integration tests.
- Added `preflight.py`; strict mode fails when `pk_core` cannot be imported,
  while `--allow-missing-pk-core` explicitly limits verification to the local
  reference model.
- Added tests for hard bounds, busy-node retention, expired-minimum recovery,
  malformed state, time regression, restored ID allocation, interval accounting,
  and constructor validation.

### Evidence and documentation fixes

- Removed the inaccurate README statement that `MASTER.md` was bundled.
- Replaced the previous blanket production-readiness implication with explicit
  package-local scope and dependency limitations.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.
- Version bumped from 4.1.0 to 4.2.0.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- Replaced optimizer-stripped behavioral `assert` checks with `_verify()`.
- Added stdlib conformance test coverage and version pinning.
- Added `VERSION` and `__version__`.

### Defects fixed

- Reordered reclaim/top-up so expired leases cannot leave the pool below its
  lower bound at the end of a tick.
- Added initial validation for invalid bounds, non-positive `per_node`, and
  non-positive `lease_ttl`.
- Added negative/NaN demand rejection.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
