# Changelog - INV-61

## 4.3.0 - 2026-09-23

Missing-components completion pass against `INV61_v4.2.0_Missing_Components_Professional_Checklist.md`
(M01-M32, 1,345 items). Per-item status: `CHECKLIST_STATUS.json`.

### Added
- `wrpc/wit.py` WIT subset parser; `wrpc/codec.py` canonical binary codec + `PK_WRPC_FRAME/2` envelope; hand-derived golden vectors.
- `wrpc/security.py` version negotiation with transcript-bound downgrade protection, PSK keyring (expiry, rotation, revocation), AES-256-GCM records, replay window.
- `wrpc/controls.py` authorizer, idempotency cache, retry policy, cancel token, admission, circuit breaker, fenced leases.
- `wrpc/ops.py` config store, audit chain, metrics, JSON logger, tracer, health, journal.
- `wrpc/node.py` TCP node + client; `tools/serve.py`, `bench.py`, `soak.py`, `sbom.py`, `run_gate_tests.py`, `checklist_status.py`.
- `pyproject.toml`, `requirements.lock`, CI workflow, eight documents under `docs/`.
- 109 new tests (123 total): property/fuzz, adversarial sockets, fault injection, two-process, concurrency.

### Fixed (found by this pass's own tests, soak and independent assessors)
- Typed errors carrying a `code` field crashed the session (`_err` keyword collision).
- `Node.stop()` left live sessions serving after "shutdown".
- In-memory audit log grew without bound (soak: +120 MB/60 s) — now a rolling window with a tracked head.
- Idempotency cache stored transient `overloaded` outcomes, so same-id retries never ran; now only final outcomes are cached.
- Idempotency key ignored which call it answered — now bound to a call digest; reuse returns `idempotency-conflict`.
- A full idempotency cache refused all new work after 100 000 calls (visible in the first soak) — now evicts oldest.
- `list<empty-record>` encoded but could not be decoded.
- Revoked/expired credentials did not end live sessions.
- `drain()` only flipped a flag — now refuses new connections/calls and waits for in-flight work.
- `audit-writable` health check was hard-coded to pass; audit failure now fails closed and flips readiness.
- Spans for typed errors were exported as `ok`; exporter exceptions could fail a call; health checks were not time-boxed.
- Client crashed on a malformed response instead of returning a typed error; `now=0` treated as "no time given" in the keyring.
- `test_component.test_version` pinned 4.2.0; installed-package import of `rpc` failed outside the source tree.
- Second assessment round: a call racing `drain()` could run after drain returned (check moved under the admission slot); a failing journal write or log sink could drop a response after the callee ran; readiness never recovered after one transient audit failure; a tampered audit file was silently extended on reload (now verified on load).


## 4.2.0 - 2026-09-22

Audit, parsing, hardening, and verification pass.

### Protocol hardening

- Extracted the dependency-free framing/dispatch primitive into `rpc.py` so core behavior can be tested without `pk_core`.
- Added exact frame-field validation, identifier/fingerprint checks, a 256-argument ceiling, finite numeric deadline validation, and fail-closed clock validation.
- Enforced interface and exact protocol-version compatibility before function lookup/dispatch.
- Changed deadline enforcement to reject calls at or after the absolute deadline.
- Added duplicate-export and callable validation.
- Removed callee exception-class disclosure from wire-visible errors.
- Added structured endpoint counters for calls, successes, malformed frames, deadline failures, version/signature mismatches, unknown functions, and callee traps.
- Canonicalized fingerprint serialization to make signature hashes spacing-independent.

### Verification and documentation

- Added 11 standalone protocol tests that execute even when `pk_core` is unavailable.
- Preserved the original 100-requirement gate tests; they remain skipped when `pk_core` is unavailable and are explicitly reported as an unresolved verification dependency.
- Removed the README claim that `MASTER.md` exists; it was absent from the supplied archive.
- Added `POST_UPDATE_AUDIT.md` with residual gaps and missing production components.
- Version bumped from 4.1.0 to 4.2.0 consistently in `VERSION`, package metadata, README, and tests.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Endpoint.handle: malformed/hostile frame (missing keys, non-list args, non-numeric deadline) crashed with KeyError/TypeError -> typed {"error": "malformed-frame"} response

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
