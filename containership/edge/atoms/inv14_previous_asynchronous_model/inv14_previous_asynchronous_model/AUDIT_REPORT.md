# INV-14 Audit Report — v4.2.0

**Element:** INV-14 — Previous asynchronous model  
**Audit date:** 2026-09-22  
**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Scope:** parse, defect audit, behavioural repair, hardening, version alignment, and missing-component inventory.

## Executive result

The 4.1.0 package parsed cleanly and compiled, but its central implementation did not satisfy its own stated contract: `PollSet.poll()` did not block until readiness or timeout. It only inspected the current flags once and returned immediately. In addition, the primitive had no synchronization around readiness state, no finite poll-set capacity, no hard wall-clock ceiling, no structured error schema, and no standalone behavioural tests that would run when `pk_core` was absent.

v4.2.0 moves the retained legacy primitive to `polling.py`, implements actual bounded waiting with race-safe wake registration, adds fail-closed validation and resource ceilings, provides structured failures and aggregate metrics, adds stable ready indexes, and adds an independent 12-test behavioural suite.

## Findings and disposition

| ID | Severity | Finding in 4.1.0 | v4.2.0 disposition |
|---|---|---|---|
| A-001 | Critical | `poll()` did not wait; an unsignalled poll returned timeout immediately regardless of `timeout_ticks`. | **Fixed.** Monotonic deadline + event wait now implement the contract. |
| A-002 | High | `ready` / `pending_signal` were unsynchronized and did not provide a real in-flight wakeup mechanism. | **Fixed.** Per-pollable lock + durable `threading.Event` waiter registration closes the lost-wakeup window. |
| A-003 | High | A malicious/invalid poll-set member could fail with incidental attribute errors rather than a controlled interface error. | **Fixed.** Members are type-checked before ownership access. |
| A-004 | High | No finite poll-set ceiling existed, permitting unbounded fan-out per call. | **Fixed.** Default maximum is 4,096 pollables and is configurable downward/upward within the hard duration model. |
| A-005 | High | Timeout ticks were integer-bounded only by caller memory/intent; there was no hard wall-clock ceiling. | **Fixed.** Maximum configured ticks plus a hard 60-second duration ceiling. |
| A-006 | Medium | Duplicate pollable names made name-only readiness results ambiguous. | **Fixed.** Duplicate names are refused; `ready_indexes` are also returned. |
| A-007 | Medium | Errors were Python exception strings only, despite checklist requirements for machine-readable failures. | **Fixed.** `PK_POLL_ERROR/1` payloads include code, details, deprecation, and migration target. |
| A-008 | Medium | Contract text referred to a “ready index” while implementation returned only names. | **Fixed.** Legacy names retained; stable indexes added. |
| A-009 | Medium | Contract declared poll outcome/refusal/set-size signals, but implementation only counted deprecated uses. | **Partially fixed.** Bounded in-memory aggregate counters now exist; external telemetry export is still missing. |
| A-010 | Medium | Behavioural tests were all skipped when `pk_core` was unavailable, producing an `OK (skipped=3)` result that could be mistaken for implementation validation. | **Fixed for the primitive.** `tests/test_polling.py` has no `pk_core` dependency and always exercises the core. Full 100-item conformance still requires `pk_core`. |
| A-011 | Medium | No explicit readiness reset lifecycle existed. | **Fixed.** `Pollable.clear()` defines re-arming after the underlying operation is consumed. |
| A-012 | Low | Core primitive and `pk_core` assessment adapter were coupled in one module. | **Fixed.** Polling behaviour is isolated in `polling.py`; `component.py` remains the framework adapter. |

## Verification performed

- Archive extraction and repository structure review.
- Python bytecode compilation of all `.py` files.
- Standalone behavioural unit tests in normal and optimized (`-O`) modes.
- Race/no-lost-wakeup stress loop.
- Actual wait/timeout timing tests.
- Foreign-owner, malformed-member, duplicate, capacity, timeout, and identity rejection tests.
- Waiter cleanup and aggregate-metric tests.
- Version consistency checks across `VERSION`, `__init__.py`, README, changelog, and conformance test.

## Verification limitation

`pk_core` is not included in this archive and was not importable in the audit environment. Therefore the framework-level claim that all 100 checklist findings pass could not be independently re-executed here. The standalone primitive is verified; the full production gate remains dependent on supplying the exact compatible `pk_core` implementation and adjacent INV/GAP components.


---

# v4.3.0 addendum — missing-components pass (2026-09-22)

Input 4.2.0 → output 4.3.0. The 35 missing components were implemented as stdlib modules, artifacts and
harnesses; all 1,593 checklist controls carry a derived state in `evidence/CHECKLIST_STATUS.json`, computed
by `tools/run_evidence.py` from what actually passed (a control whose cited evidence fails is downgraded
automatically). No control is VERIFIED: that needs an independent reviewer, and this pass refuses to review
its own work. Six defects were caught by this pass's own tests, fuzzing, release gate and clean-room run and fixed
(`docs/DEFECTS.json`). The release verdict is BLOCKED on inputs only the owner can supply: the exact
`pk_core`, a WASI 0.2 runtime and compiled component, INV-13/INV-15/GAP-15, a trusted signing key, named
owners, an approved EOL policy and the deployed-consumer inventory.
