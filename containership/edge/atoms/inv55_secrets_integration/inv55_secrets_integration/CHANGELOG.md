# Changelog - INV-55

## 4.3.0 - 2026-09-22

This release executes the v4.2.0 comprehensive missing-component checklist (100 components) as far as possible inside the repository. Final state: 49 IMPLEMENTED, 27 PARTIAL, 15 DRAFTED, 9 BLOCKED; 0 complete; production gate NO_GO. See `EXECUTION_REPORT.md`.

### Added
- `runtime/`: errors/outcome model, lifecycle state machines, wire schemas and validator, protocol negotiation, HMAC workload-token verifier, scope policy, retry/deadline/breaker/bulkhead/quota, lease cache with offline-deny/degraded policy, provider interface, in-memory provider, Vault KV v2 adapter (TLS >= 1.2, CA pin, mTLS, AppRole, namespaces), read-only failover, quarantine/freeze, hash-chained HMAC-sealed audit log, metrics/Prometheus export, scrubbed JSON logs, traces, health/readiness/stall detection, configuration schema/overlays/provenance/activation/rollback, and `SecretsService` tying them together.
- `tools/`: secret_scan, sbom, bench (with regression gate), bootstrap, build_status, gate, ci.sh. Also `.github/workflows/ci.yml`.
- `schemas/`, `fixtures/wire/`, `deploy/config/`, `deploy/vault/policies/`, `deploy/monitoring/`.
- Documentation set under `docs/`, plus SECURITY.md, CONTRIBUTING.md, CODEOWNERS, catalog-info.yaml, THIRD-PARTY-NOTICES.md and pyproject.toml.
- 110 tests (4.2.0 had 15): unit, end-to-end, 18 threat-derived adversarial tests, fuzz (1,500 random requests), a property test, concurrency, fault injection, a Vault wire double over HTTP/TLS/mTLS, failover, bootstrap and gate falsifiers.

### Changed
- The reference primitives moved to `reference.py`, which imports without `pk_core`. `component.py` re-exports them unchanged. `__init__` loads the pk_core binding lazily, so a missing pk_core still raises and is never stubbed.

### Fixed (found by this release's own tests)
- A non-list `versions` value crashed negotiation (found by fuzzing).
- The quota bucket drained when the clock went backwards.
- The Vault adapter dropped HTTP error bodies, so a sealed Vault was reported as uninitialised.
- The audit field name clashed with the verifier's value-key guard.
- The gate's result parser could silently drop a test result.


## 4.2.0 - 2026-09-22

Security and correctness hardening pass.

### Security fixes

- Replaced the `Secret(str)` subclass with a non-string `_SecretValue` container. The old design redacted `repr`, `str`, formatting, and concatenation but still leaked plaintext through inherited operations such as slicing, `encode()`, `lower()`, `replace()`, indexing, and `str.join()`.
- Blocked serialization of `_SecretValue` so secret-bearing objects cannot be accidentally pickled/deep-copied into persistence or diagnostics.
- Replaced free-form text logs with structured `AuditEvent` records that never contain secret values.
- Added strict application/secret identifier validation to reject control-character log injection and unbounded diagnostic identifiers.
- Removed the secret-name existence oracle: missing and unauthorized references now return the same external denial.
- Bound leases to the issuing broker, application, secret name, version, and an immutable lease identifier; foreign/cross-context lease reuse fails closed.
- Added explicit lease revocation and secret-version retirement checks.
- Changed lease timing to a broker-owned monotonic clock and fail closed on detected clock rollback/non-finite time.
- Validated lease TTLs as finite positive values.
- Added bounded audit retention and explicit limits for secret length, app-scope size, secret count, and per-secret version history.
- Serialized broker state transitions with an `RLock` and added concurrent-rotation coverage.

### Correctness fixes

- Corrected the lease semantics documentation: broker expiry can prevent later broker-mediated use, but plaintext already returned to application code cannot be retroactively erased. Production providers must enforce credential expiry/revocation when that property is required.
- Rotation remains append-only: existing leases stay bound to their original version until expiry, revocation, or retirement, while new resolutions receive the latest version.
- Added explicit `SecretNotFound`, `LeaseRevoked`, `LeaseContextMismatch`, `VersionRetired`, `ClockRollbackError`, and `InvalidSecretReference` failure modes.

### Verification

- Added isolated stdlib tests for redaction, serialization blocking, authorization, existence-oracle resistance, lease context binding, expiry, revocation, retirement, clock rollback, identifier validation, resource bounds, TTL validation, concurrency, and rotation.
- `compileall` passes and the focused security suite passes under normal and optimized Python.
- The repository still does not contain the external `pk_core` dependency; therefore the three `pk_core` conformance tests remain skipped in this standalone package and are not counted as verified passes.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Secret: the raw value leaked through format specs ("{:>10}".format(s)) and string concatenation ("x"+s), which contradicts "redacts itself" -> __format__ now redacts, and __add__/__radd__ return a Secret

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
