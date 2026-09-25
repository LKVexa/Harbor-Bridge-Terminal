# Changelog - INV-17

## 4.3.0 - 2026-09-23

Missing-component implementation pass (junkyard chop-shop): the 64-section checklist executed.

### Runtime
- `Stream.read_wait` / `write_wait`: bounded waits with `StreamTimeout` and `CancelToken` -> `StreamCancelled`; a timeout never implies end-of-stream.
- `write(..., idempotency_key=)`: retried writes are acknowledged once (returns `False`) inside a bounded window; `write` now returns `bool`.
- `freeze`/`unfreeze` (quarantine) with `StreamFrozen`; `stream_id`, `tenant`, `workload` on every stream; `PROTOCOL_VERSIONS`.
- `__init__` no longer imports `pk_core` eagerly (PEP 562 lazy attributes), so the runtime imports without the framework.

### New modules
- `control.py` (registry, quotas, weighted fair credit, load shedding, circuit breaker, health thresholds, emergency disable/quarantine, version negotiation, explicit crash semantics)
- `security.py` (HMAC capability tokens, single-use signed claim + fail-closed replay cache, key rotation, trust-service fail-closed, data policy, HMAC-chained audit ledger)
- `configuration.py` (schema-validated layered config, provenance, atomic activation with health-probe auto-rollback)
- `observability.py` (Prometheus exporter, JSON logs with redaction/sampling, W3C traceparent, explain, status endpoint, lineage)
- `adapters.py` (INV-15 waitable set, INV-12 canonical codec, INV-18 completion bridge, INV-20 HTTP body, INV-19 OS readiness bridge)
- `wire.py` + `schemas/` (PK_STREAM/1, PK_STREAM_CREDIT/1, PK_STREAM_CLOSE/1, error envelope, WIT)

### Dependencies
- pk_core 4.0.0 vendored from the owner's `PK_Master_Applied_All_Batches` (four estate copies byte-identical); the 100-check conformance suite now runs instead of skipping.

### Defects found and fixed during the pass
- Idempotent-duplicate check ran before the type check (a mistyped retry returned `False`).
- `enable()` lifted freezes it had not applied (manual and scope quarantines).
- `emergency_disable()` overwrote the reason of streams that were already frozen, so `enable()` then unfroze them.
- Replay cache evicted live single-use nonces under pressure (replay window re-opened); now only single-use nonces are held and a full cache fails closed.
- Single-use was verifier memory, not a token property; now a signed `su` claim.
- `HttpBody.receive_all` discarded already-read chunks when it hit `NOT_READY`.

### Verification
- 141 tests (15 suites) under `python` and `python -O`; stdlib line coverage 99.9 %, decision-branch coverage 97.8 %; ruff and mypy clean.

## 4.2.0 - 2026-09-23

Second audit, runtime separation, resource hardening, and concurrency pass.

### Runtime hardening

- Added `stream.py` as a `pk_core`-independent runtime module; `component.py` keeps compatibility re-exports.
- Replaced list FIFO storage with `collections.deque` so reads are O(1) instead of O(n).
- Added immutable `StreamConfig` ceilings for outstanding credit and in-flight buffered elements.
- Added a re-entrant lock around all shared stream state and a threaded producer/accounting regression test.
- Added stable machine-readable stream error codes/details (`StreamError.as_dict`).
- Added explicit closed/drop refusal semantics, credit reset at termination, and eager buffered-item reclamation on reader drop.
- Added atomic `StreamStats` snapshots for state, credit, backlog, stalls, transfers, reads, and dropped elements.

### Verification

- Added standalone stdlib unit/contract tests that run without `pk_core`.
- Preserved the 4.1.0 optimized-mode conformance checks and version pin, updated to 4.2.0.


## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Stream.grant: non-int credit (float, bool) accepted -> require positive int
- component.py::Stream.write: bool accepted on an int stream -> ElementTypeMismatch

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
