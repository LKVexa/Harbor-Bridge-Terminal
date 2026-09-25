# Missing Components — status after the v4.3.0 implementation pass

This file replaces the 4.2.0 gap list. It is generated from `components.json` (the machine-readable work-item
registry the evidence gate reads). Statuses are strict:

- **CLOSED_LOCAL** — implemented, negative-tested and evidenced in this repository; nothing external is needed.
- **PARTIAL** — implemented in-repo; the residual items listed need an external system, fleet or owner.
- **BLOCKED** — cannot be closed without an external decision or dependency.

Certification result of this pass: `VERIFY.py` exits **2 (BLOCKED)**. All 100 requirements are BLOCKED for
certification because the mandatory pk_core conformance suite cannot run; on local evidence alone
6 requirements verify with no external blocker and none FAIL.

| # | Work item | Component | Priority | Status |
|---|---|---|---|---|
| 1 | WI-INV20-01 | pk_core framework dependency | P0 | **BLOCKED** |
| 2 | WI-INV20-02 | WIT definitions for wasi:http service/middleware | P0 | **PARTIAL** |
| 3 | WI-INV20-03 | Asynchronous incoming/outgoing HTTP | P0 | **PARTIAL** |
| 4 | WI-INV20-04 | Typed HTTP protocol model | P0 | **CLOSED_LOCAL** |
| 5 | WI-INV20-05 | DNS and destination-identity enforcement | P0 | **CLOSED_LOCAL** |
| 6 | WI-INV20-06 | Authentication, workload identity, authorization | P0 | **PARTIAL** |
| 7 | WI-INV20-07 | TLS integration evidence (adjacent) | P1 | **BLOCKED** |
| 8 | WI-INV20-08 | Configuration subsystem | P0 | **CLOSED_LOCAL** |
| 9 | WI-INV20-09 | Supply-chain integrity and provenance | P0 | **PARTIAL** |
| 10 | WI-INV20-10 | Tenant/workload isolation | P0 | **PARTIAL** |
| 11 | WI-INV20-11 | Retry/timeout/cancellation/idempotency/backpressure | P1 | **CLOSED_LOCAL** |
| 12 | WI-INV20-12 | Health/readiness/lifecycle/stall detection | P1 | **CLOSED_LOCAL** |
| 13 | WI-INV20-13 | Failure recovery and degraded operation | P1 | **PARTIAL** |
| 14 | WI-INV20-14 | Capacity, concurrency and fairness | P1 | **PARTIAL** |
| 15 | WI-INV20-15 | Performance benchmarks and regression gates | P2 | **PARTIAL** |
| 16 | WI-INV20-16 | Structured observability | P1 | **PARTIAL** |
| 17 | WI-INV20-17 | Tamper-evident security audit log | P1 | **CLOSED_LOCAL** |
| 18 | WI-INV20-18 | Unit/contract/integration/compatibility test matrix | P0 | **PARTIAL** |
| 19 | WI-INV20-19 | Fuzzing and adversarial protocol testing | P1 | **PARTIAL** |
| 20 | WI-INV20-20 | Production ownership and escalation | P2 | **BLOCKED** |
| 21 | WI-INV20-21 | Release, rollout, rollback, emergency disable | P1 | **PARTIAL** |
| 22 | WI-INV20-22 | Support/version/patch/EOL policy | P2 | **BLOCKED** |
| 23 | WI-INV20-23 | Day-0/1/2 runbooks and incident procedures | P2 | **PARTIAL** |
| 24 | WI-INV20-24 | Backup/restore/reconstruction statement | P2 | **CLOSED_LOCAL** |
| 25 | WI-INV20-25 | Machine-readable evidence/traceability bundle | P0 | **CLOSED_LOCAL** |
| 26 | WI-INV20-26 | Packaging/build/install metadata | P0 | **PARTIAL** |
| 27 | WI-INV20-27 | CI pipeline / enforced quality gates | P0 | **PARTIAL** |

## 1. pk_core framework dependency
**Status:** BLOCKED · **Work item:** WI-INV20-01 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C003, C030, C083, C090, C093, C100

**Implemented in:** `pk_compat.py`, `pyproject.toml`, `VERIFY.py`

**Verified by:** `tests.test_ops.PackagingTest`

**Remaining to close:**
- pk_core is not shipped or published anywhere reachable; owner must name the authoritative registry/repo, license and exact version, then record its digest in evidence/dependencies/pk_core.json.

## 2. WIT definitions for wasi:http service/middleware
**Status:** PARTIAL · **Work item:** WI-INV20-02 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C010, C021, C022, C027, C029, C030, C031, C082, C083, C084

**Implemented in:** `wit/inv20.wit`, `wit/wit.lock`, `witgen.py`, `_wit_generated.py`, `wit/fixtures/`, `docs/adr/ADR-0001-wasi-http-worlds.md`

**Verified by:** `tests.test_ops.WitTest`

**Remaining to close:**
- Upstream WebAssembly/wasi-http revision is UNRESOLVED in wit/wit.lock (no network pin made).
- No component runtime (wasmtime/jco) or wit-bindgen available in the build environment: compile/instantiate, ABI and CPU-architecture matrix not executed.

## 3. Asynchronous incoming/outgoing HTTP
**Status:** PARTIAL · **Work item:** WI-INV20-03 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C011, C012, C013, C014, C015, C016, C017, C018, C021, C022, C023, C024, C025, C026, C027, C028, C029, C030, C051, C052, C053, C054, C055, C056, C057, C058, C059, C060

**Implemented in:** `aio.py`, `docs/spec/STATE_MACHINE.md`

**Verified by:** `tests.test_aio`

**Remaining to close:**
- Reference asyncio implementation only; host-binding integration with a real component runtime and real DNS/connect/TLS transport is not executed.

## 4. Typed HTTP protocol model
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-04 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C021, C022, C023, C024, C025, C026, C027, C028, C029, C081, C082, C083, C084, C085, C086, C087

**Implemented in:** `protocol.py`, `errors.py`

**Verified by:** `tests.test_protocol`

**Remaining to close:**
- HTTP/1<->2<->3 adaptation tests depend on an adjacent transport (not owned).

## 5. DNS and destination-identity enforcement
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-05 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C024, C041, C042, C043, C044, C045, C046, C047, C048, C049, C050

**Implemented in:** `egress.py`

**Verified by:** `tests.test_egress`, `fuzz`

**Remaining to close:**
- Transport must honour Destination.connect_ip; verified only against the injected resolver/transport.

## 6. Authentication, workload identity, authorization
**Status:** PARTIAL · **Work item:** WI-INV20-06 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C023, C024, C042, C043, C044, C045, C046, C047, C048

**Implemented in:** `identity.py`

**Verified by:** `tests.test_identity`

**Remaining to close:**
- Reference HMAC identity documents stand in for mTLS/SPIFFE SVIDs; deployment trust roots and rotation owner not assigned.

## 7. TLS integration evidence (adjacent)
**Status:** BLOCKED · **Work item:** WI-INV20-07 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C047, C048, C083, C100

**Implemented in:** `docs/contracts/TLS_ADJACENT_CONTRACT.md`, `egress.check_identity_coherence`

**Verified by:** `tests.test_egress`

**Remaining to close:**
- Owning transport layer not named; TLS integration transcript and rotation drill require that layer.

## 8. Configuration subsystem
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-08 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C032, C033, C034, C035, C036, C037, C038, C039, C040

**Implemented in:** `config.py`, `config/defaults.json`

**Verified by:** `tests.test_config`

**Remaining to close:** none in-repo.

## 9. Supply-chain integrity and provenance
**Status:** PARTIAL · **Work item:** WI-INV20-09 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C031, C032, C045, C090, C094, C100

**Implemented in:** `tools/release.py`, `pyproject.toml`, `SHA256SUMS.txt`

**Verified by:** `tests.test_ops.PackagingTest`

**Remaining to close:**
- No approved signing infrastructure; artifacts are digested but unsigned.
- No vulnerability scanner available offline; stdlib-only runtime has zero third-party deps, pk_core unscanned.

## 10. Tenant/workload isolation
**Status:** PARTIAL · **Work item:** WI-INV20-10 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C006, C041, C042, C043, C044, C045, C046, C047, C048, C049, C050, C059

**Implemented in:** `identity.CapabilityStore`, `aio.AdmissionController`

**Verified by:** `tests.test_identity`, `tests.test_aio.AdmissionTest`

**Remaining to close:**
- Memory/process sandbox is the component runtime's; escape testing needs that runtime.

## 11. Retry/timeout/cancellation/idempotency/backpressure
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-11 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C025, C053, C054

**Implemented in:** `aio.RetryPolicy`, `aio.CircuitBreaker`, `aio.Deadline`, `aio.AdmissionController`

**Verified by:** `tests.test_aio`

**Remaining to close:**
- Idempotency-key replay store not introduced (keys only gate retry eligibility); documented in STATE_MACHINE.md.

## 12. Health/readiness/lifecycle/stall detection
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-12 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C014, C015, C052, C071

**Implemented in:** `health.py`

**Verified by:** `tests.test_ops.HealthTest`

**Remaining to close:** none in-repo.

## 13. Failure recovery and degraded operation
**Status:** PARTIAL · **Work item:** WI-INV20-13 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C051, C052, C053, C054, C055, C056, C057, C058, C059, C060

**Implemented in:** `docs/ops/FAILURE_CATALOG.md`, `aio.py`, `health.py`, `config.py`

**Verified by:** `tests.test_aio`, `tests.test_ops.HealthTest`, `tests.test_config`

**Remaining to close:**
- In-process fault injection only; node/site/partition drills need a fleet.

## 14. Capacity, concurrency and fairness
**Status:** PARTIAL · **Work item:** WI-INV20-14 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C017, C028, C054, C061, C062, C063, C064, C065, C066, C067, C068, C069, C070

**Implemented in:** `aio.AdmissionController`, `config.py`, `docs/ops/CAPACITY_MODEL.md`

**Verified by:** `tests.test_aio.AdmissionTest`

**Remaining to close:**
- Capacity model not yet validated by controlled-hardware load tests.

## 15. Performance benchmarks and regression gates
**Status:** PARTIAL · **Work item:** WI-INV20-15 · **Priority:** P2 · **Owner:** UNASSIGNED  
**Maps to:** C061, C062, C063, C064, C065, C066, C067, C068, C069, C070, C088

**Implemented in:** `bench/run_bench.py`, `bench/baseline.json`

**Verified by:** `bench`

**Remaining to close:**
- Baseline was captured in a shared cloud sandbox, not pinned hardware; approved thresholds need owner sign-off.

## 16. Structured observability
**Status:** PARTIAL · **Work item:** WI-INV20-16 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C071, C072, C073, C074, C075, C076, C077, C078, C079, C080

**Implemented in:** `observability.py`, `docs/ops/OBSERVABILITY.md`

**Verified by:** `tests.test_ops.ObservabilityTest`

**Remaining to close:**
- Dashboards/alerts are defined as specs; no telemetry backend deployed.

## 17. Tamper-evident security audit log
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-17 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C049, C073, C078, C079

**Implemented in:** `observability.AuditLog`, `observability.verify_audit_stream`

**Verified by:** `tests.test_ops.AuditTest`

**Remaining to close:**
- WORM/append-only sink permissions are a deployment concern (documented).

## 18. Unit/contract/integration/compatibility test matrix
**Status:** PARTIAL · **Work item:** WI-INV20-18 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C029, C030, C081, C082, C083, C084, C085, C086, C087, C088, C089, C090

**Implemented in:** `tests/`, `docs/testing/TEST_MATRIX.md`

**Verified by:** `all`

**Remaining to close:**
- pk_core, runtime, INV-13/16/17/18/21 integration and compatibility rows cannot execute here.

## 19. Fuzzing and adversarial protocol testing
**Status:** PARTIAL · **Work item:** WI-INV20-19 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C041, C050, C085, C087

**Implemented in:** `fuzz/fuzz_parsers.py`, `fuzz/corpus/`

**Verified by:** `fuzz`

**Remaining to close:**
- Seeded property fuzzing only; no coverage-guided fuzzer (atheris) or sanitizers available.

## 20. Production ownership and escalation
**Status:** BLOCKED · **Work item:** WI-INV20-20 · **Priority:** P2 · **Owner:** UNASSIGNED  
**Maps to:** C009, C010, C097, C098, C099, C100

**Implemented in:** `docs/governance/OWNERSHIP.md`, `docs/governance/waivers.json`

**Verified by:** `tests.test_evidence`

**Remaining to close:**
- Named owners, approvers, on-call endpoint cannot be invented; roles are UNASSIGNED.

## 21. Release, rollout, rollback, emergency disable
**Status:** PARTIAL · **Work item:** WI-INV20-21 · **Priority:** P1 · **Owner:** UNASSIGNED  
**Maps to:** C038, C092, C093, C094, C095, C096, C097, C098, C099, C100

**Implemented in:** `identity.CapabilityStore.revoke_all`, `identity.CapabilityStore.quarantine`, `config.ConfigStore.rollback`, `docs/ops/RELEASE_AND_ROLLBACK.md`

**Verified by:** `tests.test_identity`, `tests.test_config`

**Remaining to close:**
- Canary/rollout/rollback drills require a deployment fleet.

## 22. Support/version/patch/EOL policy
**Status:** BLOCKED · **Work item:** WI-INV20-22 · **Priority:** P2 · **Owner:** UNASSIGNED  
**Maps to:** C016, C027, C093, C094

**Implemented in:** `docs/policy/SUPPORT_AND_VERSIONING.md`

**Verified by:** documentation only (no executable check)

**Remaining to close:**
- Policy drafted; SLAs/EOL dates need owner approval.

## 23. Day-0/1/2 runbooks and incident procedures
**Status:** PARTIAL · **Work item:** WI-INV20-23 · **Priority:** P2 · **Owner:** UNASSIGNED  
**Maps to:** C040, C096, C097

**Implemented in:** `docs/ops/RUNBOOKS.md`

**Verified by:** documentation only (no executable check)

**Remaining to close:**
- Runbooks not yet executed by an independent operator; drills pending.

## 24. Backup/restore/reconstruction statement
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-24 · **Priority:** P2 · **Owner:** UNASSIGNED  
**Maps to:** C057, C095

**Implemented in:** `docs/ops/STATE_AND_RECONSTRUCTION.md`, `config.bootstrap_default`

**Verified by:** `tests.test_ops.ReconstructionTest`

**Remaining to close:** none in-repo.

## 25. Machine-readable evidence/traceability bundle
**Status:** CLOSED_LOCAL · **Work item:** WI-INV20-25 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C020, C090, C100

**Implemented in:** `evidence_gate.py`, `components.json`

**Verified by:** `tests.test_evidence`

**Remaining to close:** none in-repo.

## 26. Packaging/build/install metadata
**Status:** PARTIAL · **Work item:** WI-INV20-26 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C031, C032, C040, C045, C090

**Implemented in:** `pyproject.toml`, `_version.py`, `tools/release.py`

**Verified by:** `tests.test_ops.PackagingTest`, `clean_room`

**Remaining to close:**
- License not declared (owner decision).

## 27. CI pipeline / enforced quality gates
**Status:** PARTIAL · **Work item:** WI-INV20-27 · **Priority:** P0 · **Owner:** UNASSIGNED  
**Maps to:** C070, C081, C082, C083, C084, C085, C086, C087, C088, C089, C090, C094, C100

**Implemented in:** `.github/workflows/inv20-ci.yml`, `VERIFY.py`

**Verified by:** `VERIFY`

**Remaining to close:**
- Workflow authored but never executed on an authoritative CI runner; protected-branch settings are repository-host configuration.

## What an owner must supply to move from BLOCKED to GO

1. pk_core: authoritative source, license, exact version and digest (WI-INV20-01) — unblocks the mandatory conformance suite.
2. Upstream wasi:http revision + digest in `wit/wit.lock`, plus a component runtime and wit-bindgen in CI (WI-INV20-02/03).
3. Named owners, approvers, on-call and TLS/transport layer contact (WI-INV20-20, -07); approve ADR-0001..0004 and the support policy (WI-INV20-22).
4. Signing infrastructure for artifacts, provenance and evidence (WI-INV20-09).
5. A deployment fleet / controlled hardware for rollout, rollback, fault-injection, soak and benchmark baselines (WI-INV20-13/14/15/21/23).
6. An authoritative CI runner with protected branches; re-verify the pinned action SHAs (WI-INV20-27).
