# Changelog - INV-55

## 4.3.0 - 2026-09-23

Missing-component implementation pass driven by the 100-item v4.2.0 checklist
(`docs/requirements/missing-component-checklist-v4.2.0.md`). Status per item is in
`evidence/traceability.json`; the release verdict is in `evidence/exit_gate.json` (**NO_GO**, see below).

### Added - production service
- `service.py`: `SecretsService` wiring authn -> admission -> authz -> durable audit -> provider for
  `PK_SECRET_RESOLVE/1` (resolve/use/revoke), `PK_SECRET_ROTATE/1` (rotate/retire), `PK_SECRET_SCOPE/1`.
  Lifecycle state machine (starting/ready/degraded/frozen/quarantined/draining/stopped), health/readiness/stall
  endpoint, operator freeze/unfreeze, quarantine, drain with best-effort wipe, TTL cache + opt-in stale grace
  (disconnected policy, default offline-deny), idempotent CAS rotation, write-ahead persistence of scopes/retirements.
- `providers/base.py` provider abstraction; `providers/vault.py` stdlib-only HashiCorp Vault adapter (KV v1/v2,
  namespaces, token/AppRole/Kubernetes auth, token re-login/renew-self, lease renew/revoke, sys/health incl.
  sealed/DR-secondary, TLS>=1.2 with CA pinning and mTLS, plaintext HTTP refused off-loopback).
- `identity.py` HS256 workload-token authenticator (alg pinning, iss/aud/nbf/exp) and deny-by-default policy engine
  with least-privilege role catalogue and policy digests.
- `resilience.py` deadlines/cancellation, bounded jittered retry, circuit breaker, global load shedding and
  per-authenticated-tenant/workload token buckets.
- `audit.py` hash-chained (optionally HMAC) durable audit with fsync'd 0600 file sink, verification and resume;
  audit failure fails closed.
- `telemetry.py` Prometheus exposition with bounded cardinality, redacting JSON logger, W3C trace propagation,
  decision ledger + operator explain view.
- `config.py` + `schemas/config.schema.json` + `config/` overlays: validated, layered, digest-provenanced,
  transactional activation and rollback; plaintext credential keys refused.
- `bootstrap.py` deterministic start, credential references only, audit-divergence quarantine, prod refuses
  memory provider and static tokens.
- `errors.py` stable error taxonomy (INV55-E001..E019, E999) and outcome model; JSON Schemas for every request,
  response and error in `schemas/`.

### Added - verification & governance
- 9 new test suites (contract, adversarial, Vault adapter over real HTTP/TLS, gated real-Vault, resilience/fault
  injection, config/audit/telemetry, seeded fuzz/property, concurrency, schemas/fixtures) plus secret-scan and
  release-tooling suites. 124 pass, 6 skip (mandatory, counted as NOT passed), 0 fail.
- `tools/secret_scan.py`, `tools/benchmark.py` (+ baseline), `tools/traceability.py`, `tools/release_evidence.py`
  (+ CycloneDX SBOM), `tools/exit_gate.py`; `.github/workflows/ci.yml`; `pyproject.toml`.
- ~45 architecture, requirements, security, operations, governance and performance documents under `docs/`,
  `CODEOWNERS`, `catalog-info.yaml`, `SECURITY.md`, `THIRD-PARTY-NOTICES.md`.

### Fixed during this pass (found by the new tests/benchmark)
- Tracing used the rollback-checking clock outside the error boundary: a clock rollback raised out of the public API.
- Malformed `traceparent` / non-dict requests raised `TypeError` (found by fuzzing).
- Unexpected exceptions escaped public operations; now fail closed as `INV55-E999-INTERNAL` without leaking text.
- Policy digest was recomputed on every decision (per-tenant overhead 2.73x -> 0.99x).
- Quota buckets were keyed on unauthenticated request fields (cross-tenant quota exhaustion).

### Layout
- Repository root now holds packaging, docs, tools, config, fixtures and `tests/`; the package lives in
  `inv55_secrets_integration/`. The pk_core component (`component.py`) is imported only when pk_core is present.

### Not done (see waiver register)
- Real Vault suite not executed (no Vault available in the build environment); pk_core not bundled; no artifact
  signing; no licence chosen; no owner/security/ops approvals; no fleet/soak/power measurements; rollout automation,
  SPIFFE/OIDC identity and INV-59 policy integration depend on external systems.

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
