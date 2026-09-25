# Changelog - INV-44

## 4.3.0 - 2026-09-22

Missing-components pass: applied the v4.2.0 Missing Components Professional
Checklist (19 components, 1,135 checkboxes). Nothing is claimed COMPLETE;
see `COMPONENTS_STATUS.json` (6 IMPLEMENTED_LOCAL, 9 PARTIAL, 4 BLOCKED).

### Added
- Independent compiled-output verifier (`wasm_verify.py`) and receipts bound to module sha256, toolchain identity and the full hardening profile, with freshness.
- `TenantGateway` admission path: authenticate, authorize, tenant match, admission control, receipt verification, ambient-import refusal, hardened engine, audit.
- Capability layer, tamper-evident audit log, declarative configuration store, observability, lifecycle/retry, structured error codes.
- Concrete `PK_WASM_HARDENING/1` and `PK_WASM_INSTANCE/1` JSON Schemas and a strict stdlib validator.
- in-toto/SLSA provenance in a DSSE envelope (HMAC), release gate with evidence bundle, perf suite, V8 differential tool.
- `pyproject.toml`, CI workflow, LICENSING/NOTICE/DEPENDENCIES, ops/ (owners, ADR, requirements, runbook, compatibility, waivers, alerts).

### Fixed during this pass (found by its own tests)
- Gateway registered an instance as live before its audit record was written; an audit-sink failure left a running, unaudited instance. Audit now precedes registration.
- Gateway duplicate-name check and registration were separate critical sections; names are now reserved under the lock.
- First verifier cut was structural-only and accepted 933 of 4,000 mutated modules that V8 rejects (23.3%); adding type/function/code/export cross-checks and body framing brought that to 1 of 4,000 (seed 7).
- The code-section loop shadowed the section `size` variable and broke parsing of every module with a code section (caught by the gateway tests).
- A metrics exposition test expected the wrong label order.

### Deprecated
- `Engine.instantiate(output_valid=...)` Boolean path (removal planned for 5.0.0).

### Still blocked
- MASTER.md (absent), pk_core (absent, unpinnable), licence (owner decision), Swivel toolchain integration.

## 4.2.0 - 2026-09-22

Second audit/fix/hardening pass.

### Security and correctness fixes

- Added `runtime.py` so the security-critical runtime state machine is independently testable without `pk_core`.
- Made package initialization lazy for the optional `pk_core` integration, allowing standalone runtime import/test collection without the framework installed.
- Closed direct-construction bypass: `Instance` now requires the `Engine.instantiate()` factory gate.
- Closed unbounded zero-cost execution: `Instance.step()` now requires a strictly positive integer cost.
- Made runtime state immutable to callers while retaining locked internal accounting updates.
- Added strict integer/type validation; Boolean coercions are rejected for fuel, page, and step-cost fields.
- Added per-engine immutable memory ceilings for environment-specific enforcement.
- Added control-character rejection for engine/module identifiers to protect diagnostics.
- Added locking around fuel and memory accounting to prevent same-process race corruption.
- Re-aligned custom checklist evidence with the checklist items it actually demonstrates; removed the 4.1.0 mismatched evidence claims.

### Tests and auditability

- Added standalone security tests for missing hardening features, output-verdict failure, direct-construction bypass, zero/negative/Boolean cost bypasses, immutable state, memory ceilings, identifier validation, and concurrent accounting.
- Version/repository invariant tests now run even when `pk_core` is unavailable; only the external framework conformance tests skip.
- Added `MISSING_COMPONENTS.md`, `POST_AUDIT_MATRIX.json`, and `AUDIT_REPORT.md` so missing production capabilities are explicit rather than hidden behind a generic 100-item gate claim.
- Added `CHECKSUMS.sha256` plus checksum/file-set verification in the local audit script.
- Corrected README metadata and removed the false claim that the absent master-source artifact was bundled.

### Known limitation

The supplied archive does not include `pk_core`, so the external `pk_core` conformance/gate workflow could not be executed during this pass. Standalone runtime tests and repository audits do execute locally.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Instance.step: negative cost refunded fuel, defeating metering -> ValueError
- component.py::Instance.grow: negative growth accepted -> ValueError
- component.py::Engine.instantiate: fuel<=0 / negative pages accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
