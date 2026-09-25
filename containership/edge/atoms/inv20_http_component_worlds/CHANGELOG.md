# Changelog - INV-20

## 4.3.0 - 2026-09-23

Missing-components implementation pass: executed `INV20_v4.2.0_Missing_Components_Implementation_Checklist.md`
against the 4.2.0 tree. Additive; no public name removed. Per-component status is in `MISSING_COMPONENTS.md`.

### Added
- `errors.py` stable error registry (codes, categories, retryability, bounded/escaped details, decoder that fails to a defect code).
- `protocol.py` typed request/response model; single `parse_authority` shared by policy and transport; validated `Fields` (token names, CR/LF/NUL/whitespace/non-ASCII rejection, hop-by-hop and pseudo-header refusal, field/trailer count and byte limits, duplicate-singleton ambiguity); trailer-smuggling guard.
- `egress.py` combined destination policy: authority allow-list, per-answer address classification (loopback, private, benchmark, link-local, metadata, multicast, IPv4-mapped/6to4/NAT64), mixed-answer rejection, CNAME suffix denial, TTL-capped cache, pinned `connect_ip`, per-hop redirect authorisation with loop/depth limits, TLS identity-coherence hook, ambient proxy variables ignored.
- `identity.py` typed principals, identity verification, HMAC-bound egress capabilities (tenant/workload/environment/policy digest/expiry/epoch), attenuating delegation, revocation, `revoke_all()` egress kill switch, quarantine, key rotation, fail-closed PDP wrapper with bounded cached allows.
- `config.py` `INV20_CONFIG/1` schema, secure defaults, strict validation and cross-field invariants, secret-reference enforcement, narrowing-only overlays with deterministic precedence, provenance + canonical digest, staged/atomic activation, auto-rollback on failed readiness, audited operator rollback.
- `aio.py` async lifecycle state machine, bounded async body streams with backpressure, exactly-once completions, propagating deadlines, retry policy with safety classes and bounded jitter, circuit breaker, admission control with per-tenant/workload fairness, fan-out limit.
- `health.py` lifecycle phases, readiness, stall/saturation/drain detection, `INV20_HEALTH/1` snapshot.
- `observability.py` bounded-cardinality metrics, redacted structured logs with pseudonymous tenant ids, trusted-only trace propagation, hash-chained HMAC audit log and independent verifier with anchor-based truncation detection.
- `wit/inv20.wit` (`service`, `service-with-egress`, `middleware`), `wit/wit.lock`, WIT fixtures, `witgen.py`, `_wit_generated.py`.
- `pk_compat.py`, `evidence_gate.py`, `components.json`, `pyproject.toml`, `_version.py`, `tools/release.py`, `fuzz/`, `bench/`, `docs/` (ADR-0001..0004, specs, contracts, ops, policy, governance, testing, threat model), `.github/workflows/inv20-ci.yml`.
- Eight new test modules; every suite passes normally and under `python -O`.

### Changed
- `runtime.py` exceptions also derive from `Inv20Error`; `canonical_host` additionally rejects `%` (IPv6 zone ids, percent-encoding) and backslashes.
- Package `__init__` no longer imports pk_core eagerly; `COMPONENT` loads lazily and raises a precise `PkCoreUnavailable`.
- `tests/test_component.py` no longer injects `PK_CORE_PATH`/parent directories into `sys.path`.
- Contract signal `egress_denials` is labelled by bounded reason code instead of "attempted host" (unbounded, attacker-controlled cardinality).
- `VERIFY.py` runs nine stages and fails closed (exit 0 GO / 1 NO_GO / 2 BLOCKED).

### Fixed (found while executing the checklist)
- Async dispatch polled for the response head every 1 ms, putting p99 dispatch near 1.6 ms, above the contract's 1 ms SLO. Head waiting is now event-driven; benchmark p99 is about 0.3 ms.
- A DNS answer that produced a denial could stay cached and keep denying after the record was corrected; denials are no longer cached.

## 4.2.0 - 2026-09-23

Audit, remediation, hardening, and truth-in-verification pass.

### Fixed and hardened

- Added dependency-free `runtime.py` primitives for bounded HTTP body streaming, trailer completions, host canonicalization, and explicit egress capabilities.
- Replaced O(n) list-front body forwarding with `deque.popleft()`.
- Defensive-copy mutable body chunks to immutable bytes.
- Validate body limits and world/egress configuration.
- Reject ambiguous URL/authority input at the egress host boundary.
- Added mandatory single-resolution trailer completion behavior.
- Added dependency-independent runtime/security tests.
- Added `VERIFY.py` so missing `pk_core` yields a BLOCKED exit instead of a false-green release gate.
- Added post-remediation audit and complete missing-component inventory.

### Gate

Dependency-independent tests pass. Full 100-item conformance remains BLOCKED when `pk_core` is not available.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::BodyStream.write: non-bytes chunk (str) accepted and counted by characters -> TypeError
- component.py::HttpWorld.export_handler: non-callable handler accepted, failing only at first request -> TypeError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
