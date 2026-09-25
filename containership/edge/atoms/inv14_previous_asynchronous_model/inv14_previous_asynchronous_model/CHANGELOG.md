# Changelog - INV-14

## 4.3.0 - 2026-09-22

Applies the *INV-14 v4.2.0 Missing Components Professional Engineering Checklist* (35 components,
1,593 controls). v4.2.0 semantics are unchanged; the 12 v4.2.0 tests pass untouched in normal and `-O`.
Status of every control: `evidence/CHECKLIST_STATUS.md` (machine form `.json`). Specs: `docs/COMPONENT_SPECS.md`.

### P0
- P0-01 `core_probe.py` + `deps/pk_core.lock.json`: pin/probe with stable `PK_CORE_*` codes. **Lock is UNRESOLVED** (real pk_core not supplied); release stays BLOCKED.
- P0-02 `wasi_adapter.py` + `wit/inv14-legacy-poll.wit`: PK_POLL/1 over `wasi:io/poll@0.2.0` + monotonic-clock timer; reference host only (no real runtime available).
- P0-03 JSON Schemas for all four PK_POLL contracts (+ log, audit, config, clock), generated error-code registry with retry classes, WIT enum, `docs/CONTRACT_POLICY.md`.
- P0-04 `migration.py`: forward/reverse INV-15 shims, parity check, parity-gated per-consumer state machine with rollback (protocol-level; real INV-15 not supplied).

### P1
- P1-05 `CancelToken` / `PK_POLL_CANCELLED` in `PollSet.poll(cancel=...)`; readiness wins ties.
- P1-06 `admission.py` global/tenant ceilings, optional bounded FIFO queue. P1-07 `identity.py` HMAC capability tokens binding tenant/component/instance.
- P1-08 `audit.py` hash-chained HMAC audit sink, fail-closed. P1-09 `telemetry.py` Prometheus + OTLP/JSON with bounded labels.
- P1-10 `pollog.py` PK_POLL_LOG/1. P1-11 `tracing.py` W3C trace context. P1-12/14 `lifecycle.py` 7-state model, emergency disable with drain, rollback.
- P1-13/17 `governance.py` migration registry + consumer gate, OWNERS (UNASSIGNED), CODEOWNERS. P1-15 `checkpoint.py` restart semantics (readiness never persisted).
- P1-16 `clock.py` tick authority; `PollSet(clock=...)` with an independent monotonic hard bound. P1-18 ADR-0001 (PROPOSED). P1-19 compatibility matrix.
- `service.py` composes lifecycle -> identity -> governance -> admission -> poll with audit/log/trace/telemetry.

### P2
- P2-20 adjacent-layer tests (fail in release mode, skip otherwise). P2-21 golden/negative fixtures. P2-22 `tools/fuzz.py`. P2-23 `tools/interleave.py` exhaustive model check (+ mutant).
- P2-24 `tools/bench.py` (thresholds PROPOSED). P2-25 `tools/soak.py`. P2-26 `tools/faults.py` (8 scenarios incl. SIGKILL). P2-27 fail-closed `verify_release.py` + `ci/release.yml`.
- P2-28 `tools/sbom.py` CycloneDX + unsigned in-toto provenance + stdlib-only import scan. P2-29 `tools/sign.py` Ed25519 + trust policy (only an UNTRUSTED_DEV key exists).
- P2-30 `config.py` governed config with overlays/atomic update. P2-31 `redaction.py`. P2-32 `ops/dashboard.json`, `ops/alerts.yml`. P2-33 `docs/RUNBOOK.md` + `tools/runbook.py`.
- P2-34 waiver registry. P2-35 EOL policy (PROPOSED dates) enforced by `ConsumerGate`.

### Defects found and fixed during this pass
- D-01..D-06, see `docs/DEFECTS.json` (service caught a non-exception mixin; config crash on non-JSON; code/schema disagreement on provenance keys; gate self-recursion; stale error-schema enum; signing silently needed `cryptography`, caught only by the clean-room run). Each has a regression test.

### Release verdict
`verify_release.py` exits **2 (BLOCKED)**: all local gates pass; external gates unmet — pk_core pin, trusted signature, real WASI runtime, INV-13/INV-15/GAP-15, owners/EOL approval/consumer inventory, independent review.

## 4.2.0 - 2026-09-22

Correctness and hardening pass for the retained legacy poll model.

### Critical correctness repairs

- `PollSet.poll()` now performs a real bounded wait until readiness or timeout instead of immediately returning a synthetic timeout.
- Readiness uses durable event registration plus per-pollable locking so a signal racing the poll boundary is latched and cannot be lost.
- The ready result retains legacy names and adds stable `ready_indexes` to remove identity ambiguity.
- `Pollable.clear()` defines the explicit re-arm lifecycle after the underlying ready operation is consumed.

### Hardening

- Moved the dependency-free primitive into `polling.py`; `component.py` is now the `pk_core` assessment adapter.
- Added strict type/identity validation, duplicate-handle and duplicate-name refusal, a default 4,096-member set ceiling, a configured tick ceiling, and a hard 60-second wall-clock ceiling.
- Added `PK_POLL_ERROR/1` structured error payloads with stable codes, details, deprecation marker, and migration target.
- Added `PK_POLL_METRICS/1` bounded aggregate counters for ready/timeout outcomes, invalid requests, cross-instance refusals, usage, and set-size observations.
- Foreign-owner checks fail closed before waiting; waiter registrations are removed in `finally` paths.

### Verification

- Added `tests/test_polling.py`, a 12-test stdlib suite independent of `pk_core`, including actual blocking, timeout bounds, race stress, multiple waiters, reset lifecycle, structured failures, limits, and metrics.
- Standalone tests are intended to run in normal and `python -O` modes so missing `pk_core` cannot make the behavioural core look verified only because all tests were skipped.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.

### Known release-gate dependency

- The archive still does not contain `pk_core`; therefore the full framework-level 100-requirement conformance gate cannot be reproduced from this archive alone. See `MISSING_COMPONENTS.md`.

# Changelog - INV-14

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::PollSet.poll: timeout_ticks=float('inf') (or True) bypassed the 'unbounded blocking refused' guard -> require positive int
- component.py::PollSet.poll: same pollable listed twice reported twice / inflated set_size -> ValueError on duplicates

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
