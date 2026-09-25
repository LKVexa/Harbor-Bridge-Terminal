# Changelog - INV-65

## 4.3.0 - 2026-09-22

Execution of `INV65_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST_4.2.0.md` (chop-shop job; every part build-new, no yard donors).

### Added
- Production runtime: `service.py` (ProviderService) composing identity binding (M06), authentication (M07), authorization enforcement (M08), INV-55 secret resolution with rotation/zeroize (M09), config provenance/atomic activation/rollback (M10), lifecycle state machines (M11), registry + version negotiation (M12), PK_PROVIDER_ERROR/1 envelope (M13), deadlines/cancel/retry/idempotency/backpressure (M14), admission/quotas/circuit breaker (M15), health/readiness/stall model (M16), lease fencing + residency-aware failover + degraded mode (M17), hash-chained audit (M18), AES-256-GCM state sealing + TLS 1.3 mTLS policy (M19), artifact digest pinning + SBOM/provenance (M20), telemetry with cardinality guard/redaction/trace/explain (M21), residency engine (M40).
- Durable WAL + snapshot link store with torn-tail recovery, checksums, durable tombstones, v1→v2 migration (M05); backup/verify/restore that never resurrects revoked links (M35).
- Host process + HTTP/JSON transport + service manifest (M04).
- 12 JSON schemas + stdlib validator + schema lock, golden/invalid fixtures, mixed-version matrix (M03, M24).
- Fixture backends keyvalue/http/broker and a cross-class adapter suite (M38).
- Fuzz harness (M25), fault matrix (M26), benchmark/burst/soak harness with gates (M27), compatibility matrix (M28), CI workflow + ci.sh + release gate (M29), evidence chain + verifier + PK_GATE_RESULTS (M30), 100-row RTM + checker (M31), governance/runbooks/ADR/threat model (M32, M34), rollout/canary/drain/two-person emergency disable (M33), dashboards/alerts validated against emitted metrics (M22), SLO file + error-budget evaluator (M39), pyproject + constraints (M36), NOTICE/licensing status (M37).

### Fixed (found by this pass's own fuzzing/profiling)
- Token malleability: stdlib base64 silently discarded junk characters, so altered token strings verified; decoding is now strict and canonical.
- Replay cache swept every nonce on every call (O(n) per call); now heap-ordered O(log n).
- Schema files were re-read from disk on every validation; now cached.
- Net effect on full-stack dispatch p99 on the build host: ~1.16 ms (fails the 1 ms SLO) → ~0.5 ms.
- Package `__init__` no longer imports `pk_core` eagerly, so the runtime is usable and testable without it.

### Still open (not fabricated)
- M01 MASTER.md, M02 pk_core pin, M23 real adjacent layers, M37 licence — blocked. 18 items partial with named conditions. Release gate: NO_GO.


## 4.2.0 - 2026-09-22

Audit, contract-correction, and reference-provider hardening pass.

### Fixed

- Corrected the provider model to honor `PK_PROVIDER_LINK/1` named-link semantics while preserving the 4.1 implicit `default` link API.
- Added durable `unlink()` semantics so a revoked link cannot silently reappear after restart.
- Stopped exposing the raw link table as a public attribute; callers can query link names without receiving stored configuration.
- Added stable provider error codes and fail-closed validation for identifiers and operations.
- Added bounded plain-data validation for link configuration and rejection of common inline secret fields in favor of secret references.
- Added lock-protected link/update/checkpoint/restart/health state to prevent concurrent partial state transitions.
- Moved the pure provider reference model into `provider.py`, decoupling its unit tests from `pk_core` availability.
- Added standalone isolation, revocation, secret-hygiene, invalid-input, health-gating, defensive-copy, compatibility, and concurrency tests.
- Corrected README packaging claims: `MASTER.md` is not in this archive and is now explicitly reported as missing.

### Verification

- Python compile: PASS.
- Standalone provider reference-model tests: PASS.
- Full 100-item `pk_core` conformance suite: not executable in this archive because `pk_core` is not bundled or installed in the audit environment; the tests remain present and skip rather than falsely pass.
- Post-update missing-component inventory: `AUDIT_REPORT_4.2.0.md`.


## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Provider.restart: links made after (or without) checkpoint() were silently lost on restart -> link() also records into the snapshot
- component.py::Provider.link: config missing bucket/user accepted, then call() crashed with KeyError; empty component id accepted -> ValueError at link time
- component.py::Provider.call: served calls while backend_ok was False (failure masked) -> raises ConnectionError
- component.py::Provider.health: `self.links is not None` was a vacuous check -> removed

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
