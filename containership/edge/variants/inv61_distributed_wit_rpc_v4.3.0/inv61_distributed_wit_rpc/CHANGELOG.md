# Changelog - INV-61

## 4.3.0 - 2026-09-22

Execution of the *INV-61 v4.2.0 Missing Components — Professional Engineering Completion Checklist* (M01–M32).

### Added
- Real cross-host transport: TCP with TLS 1.3 mutual auth, HELLO handshake, connection cap, accept rate limit, handshake/idle timeouts, request multiplexing, CANCEL frames, graceful drain (`transport.py`).
- Strict WIT-subset parser with normalised interface digest (`wit_model.py`) and canonical binary codec + `PK_WRPC_FRAME/2` header validated before allocation (`codec.py`).
- Version negotiation with transcript-MAC downgrade protection and a machine-readable compatibility matrix.
- Security layer: key ring with rotation/revocation, HMAC envelope bound to the TLS peer, replay guard (bounded, fail-closed, restart-safe), default-deny capability policy, HMAC-chained audit ledger.
- Resilience: idempotency cache (durable across restart), classified retry with full-jitter backoff, per-tenant token buckets, admission ceilings, per-function circuit breakers, leases with fencing epochs, emergency disable (persisted).
- Configuration subsystem with schema, overlays, secret references, provenance and atomic activation/rollback.
- Observability: liveness/readiness, Prometheus exposition with cardinality cap, redacting JSON logger, W3C trace propagation, telemetry policy.
- Packaging: `pyproject.toml`, reproducible wheel, CycloneDX SBOM, unsigned SLSA-style provenance, SHA256SUMS, verifying `bootstrap.sh` with rollback, systemd unit, Dockerfile, alerts, dashboard.
- Evidence tooling: traceability generator/checker, golden conformance fixtures, benchmark + perf gate, runtime matrix, explain view, exit gate.
- Documentation: requirements spec, architecture, threat model, operations/release/governance, performance, state inventory, telemetry policy, four ADRs (proposed), MASTER.md loss record, owners, waiver register.
- Tests: from 11 standalone protocol tests to the suites in `tests/` (property/fuzz, adversarial, concurrency, sockets, TLS, two-process, fault injection, packaging).

### Changed
- `__init__` no longer imports `pk_core` eagerly; the protocol runtime works without it and the gate integration fails with an actionable pinned-version error.
- `rpc.EndpointStats` counters are now thread-safe.

### Fixed during this pass
- Response encoding could raise when argument limits were tighter than envelope field sizes; envelope and argument limits are now separate, with a guaranteed-fit `internal` fallback.
- Replay across a process restart (empty in-memory nonce cache) is now refused (`issued-before-boot`).

### Deprecated
- `rpc.Endpoint` / `PK_WRPC_FRAME/1` in-process dict frames (removal planned 4.5.0).


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
