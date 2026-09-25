# Changelog - PLN-03

## 4.3.0 - 2026-09-23

Missing-component remediation pass against `PLN03_v4.2.0_MISSING_COMPONENT_REMEDIATION_CHECKLIST.md` (56 findings).
Per-finding status is in `REMEDIATION_STATUS.json`; nothing is marked complete without the human approval the checklist requires.

### New runtime surface
- `plane.GovernedRuntime`: the production-facing API. Every call passes lifecycle gating, capability-token verification, binding check, admission/quota, circuit breaker, deadline + bounded retry, audit, metrics and trace propagation.
- `tokens.py` capability tokens (HMAC-SHA256, key ring rotation/retirement, skew-bounded expiry, revocation hook, fail-closed outage policy) - closes the unimplemented "fail closed when token absent or expired" contract rule.
- `envelope.py` outcome model and `pk.error-envelope/1` with HTTP/gRPC mapping; `wire.py` JSON wire binding with schema validation.
- `lifecycle.py` state machine, freeze, adapter quarantine, emergency disable.
- `resilience.py` deadlines/cancellation, retry with full jitter and retry budget, token-bucket rate limiting, per-tenant concurrency fairness, circuit breaker, complete `Limits`.
- `config.py` schema-validated config, provenance ledger, atomic activation, rollback, secret refusal and redaction, constraint precedence.
- `audit_log.py` hash-chained, optionally HMAC-sealed, fsync'd audit events that resume across restart.
- `durability.py` write-ahead journal with torn-tail recovery, fencing epochs and leases, bounded offline buffer + idempotent reconciliation, residency-safe failover selection.
- `negotiation.py` mixed-version peer handshake; `telemetry.py` metrics exposition, redacted structured logs, W3C traceparent, watchdog, health/readiness; `artifacts.py` digest allowlist + provenance checks.

### Contracts, fixtures, governance
- `schemas/` (8 JSON Schemas) and `wit/pk-runtime.wit`; `fixtures/conformance/core.v1.json` language-neutral fixture.
- OWNERS.yaml (role slots, unresolved), CODEOWNERS, RACI, escalation, ADR-0001/0002 (Proposed), SHALL requirements, NFRs, semantics, compatibility/EOL, limits, threat model, failure catalog, runbooks, rollout, backup/restore, governance, exception register, integration contracts.
- pyproject.toml, DEPENDENCIES.lock.json, bootstrap.sh, CI workflow, CycloneDX SBOM, NOTICE, TRACEABILITY.json (100 items), release-evidence builder, bench regression gate.

### Defects found and fixed during remediation
- Admission: a request refused by the tenant concurrency quota still consumed a rate-limit token (found by test_mc008_mc038).
- Wire: a non-string `interface` field raised an unhashable-type error and surfaced as PK_RUNTIME_ERROR/500 (found by the wire fuzzer).
- `test_runtime.py` hard-coded the package version; it now reads VERSION.

### Verification
- 84 tests (81 run, 3 skipped for missing pk_core) pass in normal and `-O` mode; fuzz stable over 9 seeds; audit extended to every module and to per-finding artifact/test linkage.

## 4.2.0 - 2026-09-22

Second audit, correctness hardening, and evidence-integrity pass.

### Runtime fixes

- Split the operational reference runtime into dependency-free `runtime.py` for standalone verification.
- Made adapter operations thread-safe and made publish dedupe + persist + enqueue atomic.
- Added availability enforcement to `Adapter.accept`, eliminating the 4.1.0 code/changelog mismatch.
- Added length-delimited dedupe keys to eliminate ambiguous topic/idempotency collisions.
- Added documented state delete/transaction, messaging subscribe, secret fetch, and invocation surfaces.
- Added input validation, a 1 MiB inline payload ceiling, a 128-operation transaction ceiling, stable error codes/details, and fail-before-write transaction validation.

### Verification and audit integrity

- Added eleven standalone runtime tests, including a 32-thread duplicate-publish race test and package-import degradation coverage.
- Corrected checklist evidence overrides that previously marked unrelated requirements satisfied. Known incomplete requirements now remain partial.
- Corrected README's false claim that `MASTER.md` was packaged.
- Added `audit_repository.py`, `AUDIT_REPORT.md`, and machine-readable/human-readable missing-component inventories.
- The prior 4.1.0 statement that all 100 requirements were satisfied is not treated as substantiated by this standalone archive; missing production artifacts are explicitly recorded.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::DistributedRuntime.publish: idempotency key was consumed before the write, so a publish failing with AdapterUnavailable made every retry return False and the message was lost -> write first, record key only after success
- component.py::Adapter.accept: ignored availability -> raises AdapterUnavailable like get/set
- component.py::DistributedRuntime._key: empty tenant/key accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
