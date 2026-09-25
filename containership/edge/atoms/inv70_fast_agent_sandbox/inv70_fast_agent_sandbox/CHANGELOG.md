# Changelog - INV-70

## 4.3.0 - 2026-09-23

Missing-components remediation against `INV70_MISSING_COMPONENTS_REMEDIATION_CHECKLIST_4.2.0.md`. Of the 50 items previously marked MISSING, 31 are now VERIFIED, 17 PARTIAL and 2 BLOCKED. None remain MISSING. See `AUDIT_REPORT_4.3.0.md`.

### Added
- `service.py`: the governed PK_FASTBOX_RUN handler. It covers version negotiation, degraded-mode gating, caller authentication, idempotency, admission and circuit breaking, lifecycle, capability intersection, isolated execution, stable `FB-*` reason codes, audit, metrics, logs, traces, the explain view and release lineage.
- `executor.py`: single-use `spawn` worker per run with wall-clock kill, parent-side host calls with per-call timeout and budget, and a warm pool of unused workers (62.7 ms to 2.2 ms p50). Also the `WasmBackend` seam, which fails closed without the pinned engine.
- `security.py`: caller tokens, attestation, artifact/SBOM verification, fail-closed trust and time, and a hash-chained audit log.
- `resilience.py`: deadlines, cancellation, idempotency, retry policy, admission control, circuit breaker, failover selection, degraded modes and fencing.
- `config.py`: typed base/env/site overlays, provenance records, atomic activation and rollback.
- `semantics.py`: lifecycle state machine, precedence policy, protocol negotiation and the supported-version window.
- `telemetry.py`: metrics, structured logs, W3C trace context, diagnostic channel and telemetry policy.
- Tools: `bench.py` (performance suite and regression gate), `release_evidence.py` (C090), `check_lock.py`, `gen_rtm.py`.
- Governance and documentation: OWNERS, ADR-0001, deployment matrix, precedence, interfaces, Wasm runtime, configuration, performance, observability, compatibility, RUNBOOK, vulnerability/EOL policy, review schedule, EXCEPTIONS register, RTM (100 rows), alerts, dashboard, WIT draft, CI workflow, pyproject.
- Tests: 7 new suites (security, resilience, config, semantics, telemetry, integration/fault injection, fuzz, governance, wasm).

### Changed
- `contract.py`: added assumptions, interfaces v2, failure modes and signals. The startup SLO is re-scoped and a deadline SLO added.
- `runtime.py` is unchanged. Its result shape and positional API are preserved.

## 4.2.0 - 2026-09-22

Second audit, correctness and security-hardening pass.

### Runtime hardening

- Split the bounded execution primitive into dependency-free `runtime.py` so runtime security tests no longer depend on `pk_core`.
- Added exact opcode/arity validation, in-range jump validation, program-length ceiling, logical guest-memory ceiling, per-value ceiling, and strict resource-configuration validation.
- Restricted guest values to exact inert scalar types to block Python magic-method execution through attacker-controlled operands.
- Added bounded-growth checks for integer multiplication and string/bytes operations.
- Fixed stack operand order for concatenation (`left + right`).
- Hardened capability calls with bounded ASCII-safe capability identifiers, explicit denied/unbound/invalid outcomes, host-result validation, host-lookup trapping, and host-exception message redaction.
- Reject non-finite guest floats (`NaN`/`Infinity`) so results remain deterministic for downstream serialization.
- Preserved the existing `{"ok": ..., "fuel": ...}` / `{"trap": ..., "fuel": ...}` top-level result shapes and positional call arguments.

### Verification and documentation

- Added 12 dependency-free runtime/security tests and verified them under normal Python and `python -O`.
- Ran a 20,000-program deterministic randomized campaign with no uncaught runtime exceptions.
- Added `RUNTIME_SPEC.md`, `SECURITY.md`, `AUDIT_REPORT_4.2.0.md`, and machine-readable `AUDIT_MATRIX_4.2.0.json`.
- Corrected the README's nonexistent `MASTER.md` claim rather than fabricating the missing source artifact.
- Documented the critical architecture mismatch: the checklist requires a per-operation Wasm sandbox, while this repository still provides a custom Python VM.
- Recorded that `pk_core` is unavailable in the supplied repository/environment, so framework conformance tests skip and cannot be counted as release certification.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::run: `call` of a granted but unbound capability crashed with KeyError -> traps "capability unbound"
- component.py::run: mistyped operands (e.g. add str+int) escaped as TypeError -> trap "type error"
- component.py::run: malformed instructions / non-int jump targets crashed or misbehaved -> trap "invalid instruction"/"invalid jump target"
- component.py::run: negative/non-int fuel or max_stack accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
