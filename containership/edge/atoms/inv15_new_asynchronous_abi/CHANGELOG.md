# Changelog - INV-15

## 4.3.0 - 2026-09-22

Execution of the "INV-15 v4.2.0 Professional Component Checklists" (72 components, 1,599 boxes) through the junkyard chop shop.

### Added
- `host.py` — `AsyncHost` reference host: slot/generation registry with permanent retirement on generation wrap, CSPRNG token binding that fails closed (health checks: zero/repeat/collision), tenant-bound `InstanceView`s, hierarchical budgets (instance → workload → tenant → process) plus tenant fair share, memory accounting with hard/soft ceilings, deadlines/timeouts with inheritance, cancellation acknowledgement FSM, nested cancellation trees with detached children, idempotency keys, drain/quiesce, emergency disable, teardown and restart (epoch) invalidation, check-and-subscribe wakeups, blocking host-thread waits, tenant round-robin ready batches, exactly-once publication with trap state, payload ownership/release, authenticated handle serialization, explain view.
- `errors.py` (stable error envelope, cancel reasons, acks), `lifecycle.py` (normative transition table), `handles.py` (30/46-byte handle layout), `wire/codec.py` + independently written `wire/codec_alt.py`, `idl/pk_async.wit` + deterministic `tools/bindgen.py`.
- `telemetry.py` — bounded metrics with Prometheus exposition, histograms, fixed-schema sampled event log, W3C trace context, hash-chained audit.
- `adapters.py` — SCH-01 scheduler, INV-16 async-function, INV-17 stream, INV-18 completion adapters and the INV-14 pollable shim.
- Conformance corpus (66 vectors), interop harness, property/fuzz/race/lost-wakeup/soak/overload/fault-injection suites, benchmark baseline, CI script, SBOM, unsigned provenance, alert rules, dashboard, rollback hook, SPEC/threat model/runbook and policy documents.
- `tools/certify.py` — executes the checklist and writes `certification/CHECKLIST_STATUS.json`, `COMPONENT_STATUS.md`, `CHECKLIST_ANNOTATED.md`.

### Defects found by this pass's own tests (fixed)
- A clock failure during publication left the payload bytes charged to the instance while the row stayed pending; a later successful publication charged again (28-byte leak per event). Publication now takes its timestamp before mutating anything. Caught by `TestFaultInjection.test_clock_failure_does_not_corrupt`.
- The ready queue kept one entry per publication until `ready_batch()` drained it, so a guest that only used `wait`/`take` grew it without bound (13 MB over a 20,000-cycle soak). The queue is now compacted to O(live rows). Caught by `TestSoakOverload.test_soak_bounded_memory`.

### Defects found and NOT fixed (flagged)
- Declared accounting unit (256 B/row) understates measured CPython heap per live row by ~4.5x (`BENCHMARK_BASELINE.json`).
- v1 decoders reject unknown cancel-reason codes as MALFORMED — not forward-compatible (checklist 12.3).
- An idempotency key reused with a different payload is not detected (checklist 14.3).

### Unchanged
- `abi.py` (the v4.2 reference model) is kept byte-identical and is the second runtime in the interop trace.
- `component.py` / `contract.py` still need the external `pk_core` framework.

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening, and version-bump pass for the new asynchronous ABI.

### Correctness fixes

- Fixed `take()` consuming pending subtasks and returning an unset value; it now raises `SubtaskNotReady`.
- Fixed `wait()` consuming one-shot iterators twice, which caused generator-backed waits to report no ready handles.
- Fixed `call(immediate=None)` being indistinguishable from an asynchronous call; `None` is now a valid synchronous payload.
- Fixed caller-loss cleanup leaving already-ready unread results resident in the host table.
- Added direct per-handle cancellation to match the declared cancel interface.

### Security and isolation hardening

- Replaced predictable instance-local integer authority with opaque handles carrying a fresh 128-bit random token per subtask plus a diagnostic sequence number.
- Added regression coverage proving numeric sequence collisions across instances do not authorize cross-instance access and one valid handle cannot be used to synthesize another.
- Made the live host table private and exposed only a read-only snapshot.
- Added malformed/forged/retired handle validation and bounded wait-set admission.
- Bounded cancellation-reason cardinality to prevent telemetry-map growth from attacker-controlled reason strings.

### Resource and concurrency hardening

- Replaced permanently retained consumed entries with immediate live-table retirement plus a bounded tombstone cache.
- Added a re-entrant lock around host-table state transitions and concurrent allocation coverage.
- Added sequence-space exhaustion handling and constructor-time validation of instance, budget, and tombstone configuration.
- Ensured untrusted wait iterators are consumed outside the host-table lock.

### Architecture and testability

- Split the dependency-free runtime state machine into `abi.py`; `component.py` now contains only `pk_core` certification integration.
- Added lazy package exports so runtime users can import the ABI without installing `pk_core`.
- Added `tests/test_abi.py` with normal and optimized-mode coverage for lifecycle, isolation, cancellation, bounded history, wait semantics, and concurrent allocation.
- Updated contract wording, README, audit report, and missing-component inventory.

### Validation

- Python syntax compilation: PASS.
- Dependency-free ABI suite: 12/12 PASS under normal Python.
- Dependency-free ABI suite: 12/12 PASS under `python -O`.
- `tests/test_component.py`: metadata test PASS; two `pk_core` integration tests SKIPPED because `pk_core` is not present in this archive/runtime.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::AsyncAbi.complete/take: unknown handle raised bare KeyError -> ForeignHandle via _task()
- component.py::AsyncAbi.complete: completing an already-completed/consumed subtask overwrote its value -> HandleConsumed
- component.py::AsyncAbi.call: zero/negative/non-int budget not validated -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
