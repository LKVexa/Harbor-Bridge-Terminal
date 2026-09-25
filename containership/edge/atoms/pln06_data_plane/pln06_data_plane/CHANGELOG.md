# Changelog — PLN-06

## 4.3.0 — 2026-09-23

Execution of `PLN06_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v4.2.0.md` (64 work packages, Waves 0–7).

### Added
- `security.py`: rotatable HMAC key ring (active/verify-only/revoked/expiry, KMS outage fail-closed), credential authentication (audience, expiry, skew, bounded single-use replay cache, revocation), deny-by-default capability authorization with tenant scoping, signed classification labels bound to tenant+digest, hash-chained MAC-sealed fsync'd audit ledger, per-adapter authority guard, tenant namespacing.
- `integrity.py`: SHA-256 chunk manifests bound to transfer ID, out-of-order reassembly, receiver verification, bounded quarantine store.
- `transports.py`: versioned adapter SPI; in-process Component-Model-style adapter (read-only zero-copy), POSIX shared-memory adapter (namespaced, pin-limited, always unlinked), vsock VM-control adapter (control verbs only), `pk06-rpc/1` network adapter + server (version negotiation, mutual HMAC auth, TLS/mTLS, deadlines, bounded frames, manifests, quarantine), RDMA probe; adapter selection with recorded fallbacks.
- `lifecycle.py`: transfer state machine, fsync'd write-ahead journal with replay and torn-tail tolerance, fencing-epoch lease (stale controller / split-brain), backup/restore with checksum, outcome and degraded-mode tables.
- `resilience.py`: bounded retry (full jitter, deadlines, cancellation, retryable classification), circuit breaker, failure-model catalog, stall detector, residency/isolation-safe failover, seeded fault injector.
- `scheduling.py` (weighted DRR fairness), `precedence.py` (constraint precedence), `config.py` (deployment contexts, declarative config + overlays + security floor, durable history/canary/rollback/emergency-disable).
- `observability.py`: structured JSON logs with redaction, metrics registry + Prometheus exporter with cardinality cap, W3C trace-context, redacted explain view, lineage block, telemetry policy.
- `integrations.py`: GAP-13 policy client (signed, anti-downgrade, max-age fail-closed), GAP-14 signed advisory gravity hints, PLN-03 hand-off protocol, reference fixtures.
- `service.py`: `GovernedDataPlane` composing all controls; operator freeze/quarantine/drain/emergency-disable; dependency-aware health v2; metrics export; stall reaping; crash-restart reconciliation.
- Locality `vm_control` (inline-only) for the VM-control path; `PK_TRANSFER/1` enum extended (additive).
- Six new schemas; 76 new tests (92 total) incl. adversarial, mTLS, fuzz, soak, partition, disaster, contract.
- `bench/perf.py` + `bench/baseline.json`; capacity model; perf regression gate.
- Governance: `OWNERSHIP.json`, `CODEOWNERS`, `WAIVERS.json`, `TRACEABILITY.json`, docs (REQUIREMENTS, THREAT_MODEL, ADR-0002, VERSIONING, RUNBOOKS, VULNERABILITY_POLICY, TELEMETRY_GOVERNANCE, REVIEWS, OWNERSHIP), `ops/` alerts + dashboard, `config/`.
- Build/CI: `pyproject.toml` (ruff/mypy/bandit config), `.github/workflows/ci.yml`, `tools/` (run_tests, sbom, evidence, release_gate, traceability).

### Fixed
- `_StructuredError` now derives from `Exception` so the whole error family can be caught generically; accepts a per-instance `retryable` override.
- Service path: a transfer whose adapter selection failed previously kept its capacity reservation (found by the operator-controls test); it is now journaled `failed` and released.

### Findings
- TD-001: admission throughput drops from ~89k/s single-threaded to ~27k/s at 2–32 threads (lock + GIL). Scale by sharding.

### Not closed (waived, see WAIVERS.json)
Named owners, ADR approval, license choice, pk_core, real GAP-13/GAP-14/PLN-03 bindings, upstream wRPC/RDMA/wasmtime, OS sandbox, KMS/HSM, edge power data, multi-platform matrix execution, fleet soak, monitoring deployment, Sigstore, CVE scanner, MASTER.md.


## 4.2.0 — 2026-09-22

Audit, repair, hardening, and independent-runtime pass.

### Runtime hardening

- Split executable transfer logic into dependency-free `data_plane.py`; importing the package no longer requires `pk_core`.
- Made `COMPONENT` / `DataPlaneComponent` lazy exports so certification remains available when `pk_core` is installed.
- Added strict validation for residency mappings, identifiers, size, locality, digest metadata, and `inflight_limit`; booleans are no longer accepted as integers.
- Added locality-aware transport promotion while preserving legacy size-only behavior through `locality="auto"`.
- Made admission, completion, cancellation, accounting, and metrics thread-safe with an internal re-entrant lock.
- Replaced guessable sequential transfer IDs with opaque UUID4 identifiers.
- Bound completion to the exact admitted transfer metadata; a forged record cannot release another live transfer's capacity.
- Kept duplicate/unknown completion idempotent while making mismatched live completion metadata fail closed.
- Added structured stable error codes/details and retryability metadata.
- Added optional validated SHA-256 digest metadata and explicit digest algorithm fields to decisions.
- Added `PK_DATA_PLANE_METRICS/1` snapshots with admitted bytes/transfers, residency refusals, backpressure, completion, cancellation, and saturation state.
- Added optional per-tenant in-flight quotas to prevent one tenant from consuming the entire global non-inline budget when configured.
- Added atomic residency-policy replacement with revision/author/activation provenance and fail-closed protection for live transfers.
- Added `PK_DATA_PLANE_HEALTH/1` health/readiness/version/configuration/capability snapshots.
- Added JSON Schema 2020-12 artifacts for transfer, residency, transport-tier, metrics, and health contracts.

### Verification and packaging

- Added dependency-free runtime tests covering boundaries, invalid inputs, policy-copy isolation, structured errors, digest validation, backpressure, completion tamper rejection, cancellation, metrics detachment, and a 64-attempt concurrency race.
- Kept optimized-mode coverage (`python -O`) for both runtime and certification paths.
- Updated certification evidence paths after extracting the runtime.
- Synchronized package/version tests at 4.2.0.
- Corrected README claims: the input archive did not contain `MASTER.md`, so the documentation no longer claims it is shipped.
- Added `AUDIT_REPORT.md` describing unresolved production components and external dependencies.
- Added a proposed ADR, security model, operations notes, compatibility notes, and a 100-item traceability/post-audit matrix.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: expected-refusal checks gained explicit failure branches when the refusal does not occur.
- `tests/test_component.py`: added stdlib conformance coverage for 100 findings, unexpected partial/blocked findings, optimized-mode parity, and version pinning.
- Added `VERSION` and `__version__`.

### Defects fixed

- `DataPlane.complete`: duplicate/unknown completion no longer releases another transfer's in-flight slot.
- `DataPlane.admit`: rejected negative/non-integer size and empty tenant/workload values.
- `DataPlane.__init__`: rejected non-positive in-flight limits.

### Gate

The previous repository recorded all 100 checklist findings as answered when its external `pk_core` environment was available. Version 4.2.0 does not treat that declarative gate as proof that the standalone archive contains every production artifact; see the independent missing-component audit.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
