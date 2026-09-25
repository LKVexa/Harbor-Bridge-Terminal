# Changelog - INV-13

## 4.3.0 - 2026-09-22

Execution of the MC-001..MC-032 production missing-component checklists (junkyard chop-shop).

### Added (stdlib-only host layer, `host/`)
- MC-001 versioned WIT package `inv13:system-interface@4.3.0` with five least-privilege worlds, `WIT.lock`, `APPROVED_SURFACE.json` and a surface-diff/breaking-change gate.
- MC-002 Wasm binary admission (format, size, LEB128, import->capability mapping, digest allowlist) and a real engine binding (V8 via Node >= 18, core modules) with fixed instantiation order, import cross-check, trap/timeout mapping.
- MC-003 descriptor-relative filesystem: preopens are open dir fds; openat2 `RESOLVE_BENEATH|NO_SYMLINKS|NO_MAGICLINKS|NO_XDEV` with an O_NOFOLLOW component-walk fallback; rename/symlink-swap/mount-crossing adversarial tests under both resolvers.
- MC-004 capability descriptors (stable IDs, provenance, attenuation-only derivation, cascading revocation). MC-005 deny-by-default tenant-scoped policy engine with machine-readable reasons. MC-006 HMAC actor tokens with replay/expiry/audience/workload binding and fail-closed attestation gate.
- MC-007 socket provider (connect/bind/listen/DNS allowlists, numeric-address checks, quotas). MC-018 outgoing HTTP with per-hop resolved-IP vetting, IP pinning, redirect/downgrade rules, enforced TLS verification, size/time limits.
- MC-008 env/argv/stdio/secret boundary with non-inheritance and redaction; MC-009 quantised wall/monotonic clocks + guarded replay clock; MC-010 CSPRNG with bounds, rate limiting, no weak fallback, guarded deterministic provider.
- MC-011 generation-protected typed resource table; MC-012 stable error taxonomy (no host detail crosses); MC-013 bounded streams, cancel scopes, deadlines, idempotency-aware retry.
- MC-014 atomic staged config activation with CAS, crash consistency and rollback; MC-015 durable fsync'd hash-chained audit sink with HMAC checkpoints and standalone verifier; MC-016/029 bounded-cardinality metrics, outcome classes, W3C trace context, allowlist privacy filter; MC-017 hierarchical quotas + fair admission; MC-019 compatibility matrix and negotiation; MC-027 authenticated quarantine / emergency-disable / freeze / rollback controls.
- End-to-end `host/host.py` wiring identity -> policy -> descriptors -> quotas -> providers -> audit/metrics.
- MC-021..024 fuzz/property, race, fault-injection suites and benchmark harness with regression gate; MC-025/026 deterministic build, SBOM (CycloneDX 1.5), unsigned in-toto provenance, PEP 517 stdlib backend; MC-031 `tools/gate.py` evidence bundle and traceability; MC-032 ADR-001..005 and threat model T-01..T-23 tied to tests; MC-028/029/030 policy documents.
- `COMPONENT_CHECKLISTS_v4.3.0_STATUS.md` (per-item marks) and `COMPONENT_STATUS.json`.

### Fixed
- Package `__init__` hard-imported `pk_core`, so the dependency-free runtime could not be imported as a package without the framework; the assessment glue is now optional.
- (found by the new fuzzer during this pass, in new code before release) identity tokens accepted non-canonical base64 signatures (token malleability) — strict canonical decoding.

### Findings not fixed
- B-01: resolve latency SLO (p99 < 1 µs) is not met by the Python reference (measured p99 ≈ 50–60 µs). Left in contract for owner decision.


## 4.2.0 - 2026-09-22

Security hardening and audit-truthfulness pass.

### Security and correctness

- Split security-critical policy logic into dependency-free `runtime.py` so it can be tested without `pk_core`.
- `World` now snapshots caller-provided capability iterables into an immutable `frozenset`; external mutation can no longer widen authority after validation.
- Added strict type/name validation for world, component, capability, preopen, and path inputs.
- Preopen logical/host roots must be canonical single-rooted POSIX paths; relative, NUL-containing, double-slash, and normalizing (`..`, trailing-slash, etc.) roots fail closed.
- Public preopen and denial state is now read-only; callers cannot mutate the policy table through the exposed attribute.
- Changing an existing preopen requires explicit `replace=True`; silent retargeting is rejected.
- Added explicit preopen revocation and hard ceilings for path/name/preopen growth.
- Added deterministic SHA-256 hash-chained security events and chain verification without introducing ambient time authority.
- `resolve()` now labels its result `lexical-posix` and documents that production host adapters must use descriptor-relative, symlink/TOCTOU-safe filesystem operations.

### Verification and audit clarity

- Added dependency-free regression tests for mutable-capability escalation, read-only preopens, canonical-root validation, traversal/absolute/NUL rejection, explicit replacement, revocation, and audit-chain integrity.
- Updated evidence references from `component.py` to the actual implementation in `runtime.py`.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`; checklist accounting is no longer presented as proof that a full production WASI host exists.
- Version pins updated to 4.2.0.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Instance.grant_preopen: accepted empty logical name or relative host root (resolution then relative to CWD) -> ValueError
- component.py::Instance.resolve: preopen root '/' refused every valid path (prefix became '//'); NUL bytes not refused -> correct prefix computation, refuse NUL as PathEscape

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
