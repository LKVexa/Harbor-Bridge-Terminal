# Changelog - INV-19

## 5.0.0 - 2026-09-23

Missing-components pass: MC-01..MC-28 of `INV19_v4.2.0_Missing_Components_Comprehensive_Checklist.md` executed (junkyard chop-shop, build-new; no donor code).

### Added
- Native backends: io_uring (raw syscalls + mmap, verified on Linux 6.18 x86-64), epoll, portable (`selectors`), kqueue and IOCP adapters (implemented; not executable on this host).
- Operational capability probes and reason-coded, deterministic selection; administrative disable, diagnostic override, quarantine and failover.
- `AsyncHost` driver with exactly-once operation table (generation-tagged 64-bit ids), INV-18 futures, INV-17 credit streams, INV-15 waitable sets.
- Canonical error taxonomy `PK_ASYNC_ERROR/1`; JSON Schemas for all interfaces with frozen v1 copies and a breaking-change checker.
- Typed configuration with precedence, atomic activation, rollback and provenance; deadlines, bounded retry, admission control, circuit breaker; per-scope resource accounting.
- HMAC capabilities with expiry/revocation/rotation; central redaction; hash-chained audit log with Ed25519-signed checkpoints and an offline verifier.
- Metrics (Prometheus text, label allow-lists), structured logs, W3C trace context, decision/explain log, alert rules, dashboard.
- Evidence gate (`tools/run_gate.py`): 100 requirement records, chained + signed bundle, independent verifier, negative self-test including two known-bad mutants.
- Benchmark, soak/burst/fleet/disaster, certification-matrix and supply-chain (CycloneDX SBOM, signed manifest) tools; governance set.

### Fixed (found by this pass's own tests)
- io_uring reaper never flushed the kernel's CQ-overflow backlog, so one overflow stalled the ring permanently (found by the soak burst; regression test added and shown to fail on the old code).
- Quarantining the active backend re-initialised it instead of failing over.
- Under descriptor exhaustion `AsyncHost()` crashed with a raw `OSError`; start-up now refuses with `BackendUnavailable(NO_USABLE_BACKEND)` carrying per-backend `PROBE_FAILED:<canonical code>` reasons (found by the 256-fd certification cell).
- The 256-caller concurrency test leaked its descriptors on failure and cascaded into 58 unrelated failures under a low fd limit; it now scales to the fd budget and reports the reduced size as BLOCKED.
- Config coercion let `int(inf)` escape as `OverflowError` and silently truncated `1.5` to `1` (found by config fuzzing; corpus entries R5/R6).

### Changed
- `tests/test_component.py`: the pk_core presence failure is tagged `DEPENDENCY_UNAVAILABLE` so the gate reports BLOCKED, distinct from a component test failure; the suite still cannot go green without pk_core.

## 4.2.0 - 2026-09-23

Audit, correctness and hardening pass.

### Backend correctness/hardening

- Extracted the backend state machine to a `pk_core`-independent module and added deterministic backend priority.
- Added descriptor/configuration validation, explicit cancellation, thread-safe state transitions, fallback engagement accounting, and bounded diagnostic snapshots.
- Fixed empty-string completion errors being interpreted as successful values (`error is not None` is now authoritative).
- Added self-contained tests including concurrent descriptor-budget enforcement.

### Audit integrity

- Package primitives remain importable without `pk_core`, but production component integration is explicitly unavailable.
- Added an unskipped dependency-presence test so a missing `pk_core` cannot produce an all-skipped false-green conformance run.
- Added `AUDIT_REPORT.md` and machine-readable `MISSING_COMPONENTS.json` enumerating the remaining production gaps.
- Production status is PARTIAL until the external gate and missing native/integration/operations evidence are supplied.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::AsyncBackend.post: posting to an unarmed fd implicitly armed it, bypassing the descriptor budget; second post overwrote unreaped completion (lost error) -> ValueError for both
- component.py::AsyncBackend: unknown backend name only failed later with KeyError -> NoBackend at construction
- component.py::AsyncBackend.arm: re-arming an armed fd reset its pending event -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
