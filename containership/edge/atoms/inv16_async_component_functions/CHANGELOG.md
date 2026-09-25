# Changelog - INV-16

## 4.3.0 - 2026-09-23

Missing-components closure pass against `INV16_v4.2.0_Missing_Components_Closure_Checklist.md`
(42 items: 16 PASS, 25 PARTIAL, 1 BLOCKED - see `docs/CLOSURE_LEDGER.md`).

### Behaviour changes (read before upgrading)

- `cancel()` on an already-terminal call now raises `AlreadyTerminal` (was `DoubleDelivery`/`CallCancelled`/
  `CallTrapped`) and no longer increments `double_delivery_attempts`; the first terminal cause is preserved.
  `DoubleDelivery`, `CallCancelled`, `CallTrapped`, `AlreadyTerminal` share the base `TerminalConflict`.
- Terminal history is bounded (`tombstone_capacity`, default 65,536). Ids that were issued but aged out raise
  `HistoryExpired` (a `ValueError`), never "never issued" and never accepted.
- Build-time attributes (`declared`, `stateful`, `reentrancy`, `instance`, `transport`, ...) can no longer be
  reassigned after construction (`AttributeError`) - closes a declaration-tampering path found by the new
  security suite.
- The package imports without `pk_core`; pk_core-dependent names (`COMPONENT`, `build_contract`, ...) load lazily.

### Added

- Real sync->async bridge (`bridge.py`), canonical ABI transport (`abi.py`), declaration descriptors
  (`declare.py`), reference lowering (`lowering.py`), observability (`observability.py`), preflight.
- Structured `CancelReason`, per-function re-entrancy policy (allow/refuse/bounded queue), finite-width call-id
  allocator with generations, W3C trace context, `inv16.event/1` events dispatched outside the lifecycle lock,
  deterministic fault-injection points, `TRANSITIONS` contract table, `snapshot()`.
- Surrogate INV-15/10/17/20 fixtures; 13 new test suites (110 tests total); benchmarks; soak; reproducible
  release builder with SBOM, provenance and signing hook; rollback and canary automation; CI workflow;
  threat model, runbook, ADRs, compatibility matrix, alerts and dashboard; LICENSE/NOTICE; hash-chained
  evidence bundle and verifier.

### Defects found and fixed during closure

- A fault between completing a call and promoting the next queued call could strand the queue
  (fault points are now all evaluated before any mutation).
- Attribute reassignment could swap the frozen declaration table (threat T4).
- `near-exhaustion` event would have fired on every invoke past the threshold (now once per generation).
- 4.2.0 `__init__` imported `component.py`, making the pk_core-free runtime unimportable as a package.

### Verification

- 110 tests (3 pk_core conformance tests skipped, never counted) pass on CPython 3.10, 3.11, 3.12, 3.13, each
  in normal and `-O` mode; stdlib lint 0 findings; line coverage gate passes with critical lifecycle functions
  fully covered. Numbers for this build are in `evidence/INV16_LOCAL_GATE.json`.

## 4.2.0 - 2026-09-23

Audit, correctness and concurrency-hardening pass.

### Runtime hardening

- Split the executable async lifecycle model into `runtime.py`, allowing its safety-critical behavior to be tested without `pk_core`.
- Freeze the build-time declaration map and validate declaration/stateful/concurrency-limit inputs so async-ness cannot be mutated after construction.
- Serialize invoke/complete/cancel/trap transitions with an `RLock`, closing check-then-insert races in re-entrancy admission and call-id allocation.
- Implement the previously declared concurrency-limit, cancellation, and callee-trap failure modes.
- Retain terminal-state tombstones so completed, cancelled, trapped, and never-issued calls are distinguished; late delivery after cancellation/trap is rejected explicitly.
- Add counters for concurrency refusal, double-delivery attempts, cancellations, and traps.
- Make `is_async()` reject undeclared functions consistently with `invoke()` rather than returning an inferred false value.

### Verification

- Added `tests/test_runtime.py`: five stdlib-only tests covering immutable declarations, exactly-once delivery, terminal reasons, limits/re-entrancy, trap cleanup, and parallel unique-id issuance.
- `compileall` passes and all five standalone runtime tests pass under Python 3.13.
- The three `pk_core` conformance tests remain present but are skipped in this isolated archive because the sibling `pk_core` package is not bundled.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::AsyncFunctions.complete: second delivery raised KeyError (DoubleDelivery path was dead code since state is deleted) -> DoubleDelivery for issued ids, ValueError for never-issued; assess now catches only DoubleDelivery
- component.py::AsyncFunctions.invoke: undeclared functions silently treated as sync, contradicting 'fixed; never inferred' -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
