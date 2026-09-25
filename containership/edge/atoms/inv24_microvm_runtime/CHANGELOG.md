# Changelog

## 4.3.0 — 2026-09-23 — missing-component implementation pass

Executed `INV24_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` across all 64 components.

- Added typed Firecracker adapter, VMM supervisor, KVM ioctl preflight, device specs + ownership
  registry, snapshot store, PLN-04 admission controller, INV-35 datapath negotiation.
- Added configuration subsystem, secrets/redaction, artifact pinning, keyring, capability tokens,
  hash-chained audit log, jailer/cgroup/seccomp policy and live isolation verifier.
- Added retry/deadline/cancel, circuit breaker, fencing leases + idempotency journal, health/stall
  monitor, quarantine/freeze/degraded-mode controls.
- Added metrics (bounded cardinality, Prometheus text), structured logs, W3C tracing, decision records.
- Added 10 JSON Schemas + validator; 89 passing tests (unit, contract, adversarial, property/fuzz,
  concurrency, fault injection) and 9 explicit NOT_TESTED real-host/framework tests.
- Added docs (ownership, ADR, requirements, compatibility, interfaces, threat model, SLO, rollout,
  security policy, runbooks, incident response, reviews, telemetry, performance), CI workflow,
  packaging, evidence producer, traceability and a deterministic production exit gate.
- Fix found by fuzzing: `Keyring.verify` raised `TypeError` on non-ASCII MACs; now returns False.
- Production gate verdict: **NO_GO** (owners, pins, real-host evidence outstanding).

# Changelog - INV-24

## 4.2.0 - 2026-09-23

Repository audit, isolation hardening, and verifiable standalone-runtime pass.

### Fixed / hardened

- Extracted the safety-critical microVM lifecycle model into `runtime.py`, with no `pk_core` dependency, so the core rules can be imported and tested from an isolated checkout.
- Made `pk_core` integration lazy in `__init__.py`; importing the package no longer fails merely because the external certification framework is absent.
- Added strict text validation for instance/tenant IDs, rejecting empty values, control characters, overlong values, and non-strings.
- Added strict integer/type validation for vCPU, memory, boot budget, and elapsed time; booleans/floats no longer pass as integer configuration.
- Added explicit upper/lower vCPU and memory ceilings.
- Sealed tenant, device, resource, state, destruction, and boot-timing fields after construction so callers cannot bypass validation by mutating an existing instance.
- Added a stable `PK_MICROVM/1` creation record and `PK_MICROVM_STATUS/1` status snapshot.
- Made destruction terminal and explicit; repeated stop and post-destruction lifecycle operations are refused.
- Corrected README integrity claim: `MASTER.md` is not present in the supplied archive.

### Verification

- Added `tests/test_runtime.py`: 10 standalone tests covering importability, version, schemas, validation, limits, device refusal, budget enforcement, lifecycle, terminal destruction, mutation resistance, and snapshot isolation.
- Python compilation succeeds for all source/test modules.
- Framework conformance tests remain dependency-gated because `pk_core` was not supplied; this is now reported as an external verification gap rather than mistaken for a passing test run.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::MicroVM.boot: budget_ms override let a caller widen the declared 125ms boot budget arbitrarily (budget bypass) and negative elapsed_ms was accepted -> budget must be in (0, BOOT_BUDGET_MS], elapsed_ms >= 0, else ValueError
- component.py::MicroVM.__post_init__: empty name/tenant accepted; a str devices value was split into characters; mutable sets stored as-is -> ValueError/TypeError, normalise to frozenset

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
