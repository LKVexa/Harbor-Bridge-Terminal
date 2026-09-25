# INV-29 Hybrid Wasm/unikernel — 4.3.0 Missing-Components Implementation Report

**Version:** 4.3.0 · **Date:** 2026-09-23 · **Input:** 4.2.0 hardened archive + *INV29 v4.2.0 Missing Components Implementation Checklist* (103 items)
**Source digest:** `sha256:374cf4281db813cb9dc01ecd207d4bda4ab8bdb46730a82b0a9039b1f9ec4ad3` · **Gate:** `conformance/PK_GATE_RESULTS.json` → **NO_GO** (machine-derived; 29 P0 blockers)

## Result
Every one of the 103 components was worked. All of the in-archive work is implemented and has evidence behind it. Anything that needs the estate is marked as blocked, with the reason, and is not claimed as closed.

| Status | Count | Meaning |
|---|---:|---|
| CLOSED | 48 | implemented and evidenced in this archive; the Definition of Done needs nothing external |
| IMPLEMENTED_LOCAL | 30 | code, tests and docs are done; the Definition of Done still needs an external environment or exercise |
| OWNER_ACTION | 9 | needs the owner: licence, signing key, MASTER.md, named owners and on-call, ratified SLO/SLA/retention values |
| BLOCKED_EXTERNAL | 16 | pk_core, INV-11/27/44/30, PLN-04, hypervisor/runtime/ISA/TPM labs |

The verdict is **NO_GO**, and that is correct: the checklist forbids waiving P0 items and forbids skipping certification-critical tests. pk_core conformance still shows 3 skips.

## Validation
* `tools/run_tests.py`: 15 standalone suites, **232 tests pass** under both normal Python and `python -O`. `test_component.py` (pk_core) is SKIPPED and counted as certification-critical.
* A 25,000-iteration fuzz run on 4 targets found nothing. The property suite covers 400 seeded cases. A 16-thread race test showed no double admission. A soak/burst test showed no retained-memory growth beyond the bounded replay cache.
* `tools/bench.py`: admit p50 0.14 ms, p99 0.24 ms. The perf regression gate passes.
* The secret scan is clean. SBOM, SHA256SUMS, provenance (unsigned), traceability and the evidence manifest were generated. The 5-entry evidence ledger chain is intact.
* An independent adversarial review ran in two rounds. It found 10 defects, including **2 critical admission bypasses** (type confusion via frozenset/str subclasses). All 10 are fixed and have regression tests (see CHANGELOG).

## Per-component status

| ID | Pri | Component | Status | Blocker / evidence |
|---|---|---|---|---|
| INV29-MC001 | P0 | pk_core runtime package | BLOCKED_EXTERNAL | pk_core is not available in this environment: startup compatibility assertion, adapter boundary, lazy import and negative fixtures (absent/old/new-major/missing submodules) are implemented and tested, but the 100-item assessment, run/gate/verify and a digest pin need the real package. |
| INV29-MC002 | P0 | INV-11 Interface contract language | BLOCKED_EXTERNAL | INV-11 not installed. Local typed layer + the full breaking/additive fixture set are implemented and enforced in admission in addition to name closure; INV-11 remains the authority and is required for closure. |
| INV29-MC003 | P0 | INV-27 Unikernel execution | BLOCKED_EXTERNAL | INV-27 not available. Sealed-image attestation contract, adapter with timeout/retry/breaker and a labelled fault-injecting test double exist; a real INV-27 integration run is required. |
| INV29-MC004 | P0 | INV-44 Wasm hardening system | BLOCKED_EXTERNAL | INV-44 not available. Hardened-module attestation contract + test double exist; real INV-44 integration run required. |
| INV29-MC005 | P0 | PLN-04 Execution plane | BLOCKED_EXTERNAL | PLN-04 not available. verify_record() is the consumer contract and ExecutionPlaneTestDouble proves unsigned records are refused; PLN-04 must adopt it. |
| INV29-MC006 | P2 | INV-30 Capability hardware sandbox | BLOCKED_EXTERNAL | INV-30 (optional) not available; schema reserves the 'hardware-capability' layer and policy.required_layers=3 already refuses without it. Applicability decision is the owner's. |
| INV29-MC007 | P0 | MASTER.md | OWNER_ACTION | MASTER.md (the 100 per-item master prompt/workflow documents) is the owner's source material and is not in the archive; it cannot be reconstructed without inventing content. Owner to supply. |
| INV29-MC008 | P0 | Machine-readable schema for PK_HYBRID_COMPOSITION/1 | CLOSED | schemas/pk_hybrid_composition_1.schema.json, records.py, tests/test_records.py |
| INV29-MC009 | P0 | Machine-readable schema for PK_HYBRID_VERIFICATION/1 | CLOSED | schemas/pk_hybrid_verification_1.schema.json, records.py, tests/test_records.py |
| INV29-MC010 | P0 | Typed capability/interface definitions | CLOSED | interfaces.py, tests/test_interfaces.py |
| INV29-MC011 | P0 | Schema evolution / compatibility policy | CLOSED | docs/SCHEMA_EVOLUTION.md |
| INV29-MC012 | P0 | Formal architecture document / data-flow diagram | CLOSED | docs/ARCHITECTURE.md |
| INV29-MC013 | P0 | Dedicated threat model artifact | CLOSED | docs/THREAT_MODEL.md |
| INV29-MC014 | P1 | pyproject.toml / package metadata | CLOSED | pyproject.toml |
| INV29-MC015 | P1 | Pinned dependency manifest / lockfile | IMPLEMENTED_LOCAL | Runtime is stdlib-only and locked; pk_core cannot be pinned by digest until its artifact is available. |
| INV29-MC016 | P1 | Supported Python-version declaration | CLOSED | pyproject.toml, .python-version, .github/workflows/ci.yml |
| INV29-MC017 | P1 | SBOM | CLOSED | sbom/inv29.cdx.json, tools/build_release.py |
| INV29-MC018 | P1 | Build provenance / attestation | IMPLEMENTED_LOCAL | SLSA-style provenance statement is generated but unsigned; needs a trusted builder identity and signing key. |
| INV29-MC019 | P1 | Release signature / checksum manifest | OWNER_ACTION | Checksum manifest generated; release signature needs the owner's signing key (not something to mint here). |
| INV29-MC020 | P1 | License file and notices | OWNER_ACTION | No LICENSE chosen. NOTICE states no third-party code is bundled; the licence decision is the owner's. |
| INV29-MC021 | P1 | Vulnerability scanning configuration/results | IMPLEMENTED_LOCAL | No third-party runtime packages to scan; interpreter and external elements (pk_core, INV-*) are not scanned here — needs a CVE feed/scanner in CI. |
| INV29-MC022 | P1 | Secret scanning configuration/results | CLOSED | security/secret_scan.json, tools/secret_scan.py, .github/workflows/ci.yml |
| INV29-MC023 | P0 | Executable pk_core conformance in this archive | BLOCKED_EXTERNAL | pk_core conformance cannot run here; run_tests.py counts its skips as certification-critical so the gate stays NO_GO. |
| INV29-MC024 | P0 | Public-interface contract tests for serialized records | CLOSED | tests/test_records.py |
| INV29-MC025 | P0 | INV-11 integration test fixture | BLOCKED_EXTERNAL | Typed fixtures exist locally; an INV-11 fixture run needs INV-11. |
| INV29-MC026 | P0 | INV-27 integration test | BLOCKED_EXTERNAL | Integration-shaped tests run against a labelled INV-27 double only. |
| INV29-MC027 | P0 | INV-44 integration test | BLOCKED_EXTERNAL | Integration-shaped tests run against a labelled INV-44 double only. |
| INV29-MC028 | P0 | PLN-04 integration test | BLOCKED_EXTERNAL | Integration-shaped tests run against a labelled PLN-04 double only. |
| INV29-MC029 | P0 | Cross-architecture compatibility matrix/tests | BLOCKED_EXTERNAL | Decision logic covered for every ISA/target pair; real x86_64/aarch64 execution of wasm32/wasm64 inside a unikernel needs a hardware lab (CI matrix covers the element itself on x86_64 + arm64 runners). |
| INV29-MC030 | P0 | Hypervisor compatibility tests | BLOCKED_EXTERNAL | Needs Firecracker/KVM/Hyper-V/Xen lab via INV-27. |
| INV29-MC031 | P0 | Wasm runtime compatibility tests | BLOCKED_EXTERNAL | Needs Wasmtime/WAMR/Wasmer/WasmEdge runs via INV-44. |
| INV29-MC032 | P0 | Fuzzing harness | CLOSED | fuzz_targets.py, tools/fuzz.py, tests/test_fuzz.py |
| INV29-MC033 | P0 | Property-based tests | CLOSED | tests/test_properties.py |
| INV29-MC034 | P0 | Concurrency/race tests | CLOSED | tests/test_concurrency.py |
| INV29-MC035 | P0 | Security adversarial tests | CLOSED | tests/test_admission.py, tests/test_records.py, tests/test_regressions_review.py |
| INV29-MC036 | P0 | Benchmark suite | CLOSED | tools/bench.py, perf/baseline.json |
| INV29-MC037 | P0 | Soak/burst/fleet-scale tests | IMPLEMENTED_LOCAL | Sustained + burst admission is tested per process; fleet-scale (multi-replica, shared replay state) needs an estate. |
| INV29-MC038 | P0 | Failure-injection / chaos tests | IMPLEMENTED_LOCAL | Fault injection (timeout, crash, malformed, absent, revoked) runs against doubles; real dependency chaos needs the estate. |
| INV29-MC039 | P0 | Disaster / partition / reconnect tests | IMPLEMENTED_LOCAL | Store loss/restore/reconstruct and partition/reconnect (breaker) are tested locally; degraded-control-plane drills need the estate. |
| INV29-MC040 | P0 | Machine-readable certification evidence | IMPLEMENTED_LOCAL | Hash-chained ledger bound to the source digest exists; certification evidence proper requires the pk_core run. |
| INV29-MC041 | P0 | Gate output artifact | IMPLEMENTED_LOCAL | Gate artifact is generated and machine-derived; its current verdict is NO_GO, so a *successful* gate artifact does not exist yet. |
| INV29-MC042 | P0 | CI pipeline | IMPLEMENTED_LOCAL | Workflow authored (compile, unit, -O, conformance, fuzz, perf, scans, packaging, evidence); it has not run in a forge yet. |
| INV29-MC043 | P0 | Authentication mechanism | IMPLEMENTED_LOCAL | Artifacts and records are authenticated; caller authentication (mTLS/workload identity on whatever transport fronts admit) belongs to the deployment and is not present. |
| INV29-MC044 | P0 | Authorization / policy engine integration | IMPLEMENTED_LOCAL | Local policy engine (tenant allow-list, denylist, cardinality, provenance, generations) implemented; integration with the estate policy engine (e.g. OPA) needs that engine. |
| INV29-MC045 | P0 | Tenant identity binding | CLOSED | admission.py, lifecycle.py, tests/test_admission.py |
| INV29-MC046 | P0 | Workload identity / attestation binding | IMPLEMENTED_LOCAL | Workload identity is bound through the module digest + hardened attestation; SPIFFE/workload-attestation integration is external. |
| INV29-MC047 | P0 | Host image identity / digest binding | CLOSED | admission.py, tests/test_admission.py |
| INV29-MC048 | P0 | Wasm module identity / digest binding | CLOSED | admission.py, tests/test_admission.py |
| INV29-MC049 | P0 | Cryptographic verification of sealed | IMPLEMENTED_LOCAL | sealed is now cryptographically verified (HMAC-SHA256, subject-bound, fresh, revocable); production needs asymmetric signatures from INV-27. |
| INV29-MC050 | P0 | Cryptographic verification of hardened | IMPLEMENTED_LOCAL | hardened verified the same way; production needs asymmetric signatures from INV-44. |
| INV29-MC051 | P0 | Measured-boot / TPM / confidential-compute evidence | BLOCKED_EXTERNAL | Policy can require a measured-boot attestation and refuses without it; real TPM/confidential-compute evidence needs hardware. |
| INV29-MC052 | P0 | Capability provenance | CLOSED | admission.py, tests/test_admission.py |
| INV29-MC053 | P0 | Capability denylist / dangerous-capability policy | CLOSED | admission.py, tests/test_admission.py |
| INV29-MC054 | P0 | Capability cardinality policy per workload/tenant | CLOSED | admission.py, tests/test_admission.py |
| INV29-MC055 | P0 | Replay protection / record freshness | IMPLEMENTED_LOCAL | Nonce + TTL + attestation freshness implemented and race-tested; the replay cache is per-process, so multi-replica deployments need a shared store. |
| INV29-MC056 | P0 | Record integrity/signature | IMPLEMENTED_LOCAL | Records are signed and verified (HMAC); asymmetric signing so consumers cannot forge needs the owner's key infrastructure. |
| INV29-MC057 | P0 | Secure serialization/parser | CLOSED | records.py, fuzz_targets.py, tests/test_records.py |
| INV29-MC058 | P0 | Secret handling / redaction rules in code | CLOSED | records.py, telemetry.py, tests/test_records.py |
| INV29-MC059 | P1 | Persistence model | CLOSED | lifecycle.py, docs/PERSISTENCE.md, tests/test_lifecycle.py |
| INV29-MC060 | P1 | Idempotency contract | CLOSED | lifecycle.py, docs/PERSISTENCE.md, tests/test_lifecycle.py |
| INV29-MC061 | P1 | Lifecycle state machine | CLOSED | lifecycle.py, docs/PERSISTENCE.md, tests/test_lifecycle.py |
| INV29-MC062 | P1 | Reconciliation loop | CLOSED | lifecycle.py, tests/test_lifecycle.py |
| INV29-MC063 | P1 | Revocation handling | CLOSED | lifecycle.py, admission.py, tests/test_lifecycle.py |
| INV29-MC064 | P1 | Rollback implementation | IMPLEMENTED_LOCAL | Policy rollback and evidence-anchored rollback tooling exist and are tested; not yet exercised in a non-production estate. |
| INV29-MC065 | P1 | Emergency-disable implementation | CLOSED | lifecycle.py, tools/inv29ctl.py, service.py |
| INV29-MC066 | P1 | Backup/restore/reconstruction implementation | CLOSED | lifecycle.py, tools/inv29ctl.py, tests/test_lifecycle.py |
| INV29-MC067 | P1 | Dependency timeout/retry/circuit-breaker behavior | CLOSED | deps.py, tests/test_deps.py |
| INV29-MC068 | P1 | Partial-failure handling around external verifiers | IMPLEMENTED_LOCAL | Partial/failed verifier responses fail closed against doubles; real verifier behaviour needs the dependencies. |
| INV29-MC069 | P1 | Baseline performance data | IMPLEMENTED_LOCAL | Reference baseline captured on CI-class hardware; must be re-captured on the production node class. |
| INV29-MC070 | P1 | p50/p95/p99/worst-case thresholds | OWNER_ACTION | p50/p95/p99/worst thresholds proposed; owner ratification required. |
| INV29-MC071 | P1 | Load/overload measurements | IMPLEMENTED_LOCAL | Thread-scaling and overload behaviour measured locally; production load test needs the estate. |
| INV29-MC072 | P1 | Per-tenant/per-workload overhead measurements | IMPLEMENTED_LOCAL | Per-admission overhead measured; per-tenant overhead in a live estate not measured. |
| INV29-MC073 | P1 | Copy/serialization/context-switch analysis | CLOSED | docs/CAPACITY.md, tools/bench.py |
| INV29-MC074 | P1 | Optimization evidence | IMPLEMENTED_LOCAL | Hot-path optimisation noted; further optimisation needs production profiles. |
| INV29-MC075 | P1 | Memory/concurrency/queue operational limits | CLOSED | docs/CAPACITY.md, model.py, records.py |
| INV29-MC076 | P2 | Power/thermal measurements | BLOCKED_EXTERNAL | Power/thermal needs far-edge hardware; applicability is the owner's decision. |
| INV29-MC077 | P1 | Capacity model and saturation thresholds | IMPLEMENTED_LOCAL | Capacity model defined from the reference baseline; needs production inputs. |
| INV29-MC078 | P1 | Performance regression gate | CLOSED | tools/bench.py, .github/workflows/ci.yml |
| INV29-MC079 | P1 | Health endpoint | CLOSED | telemetry.py, tests/test_telemetry.py |
| INV29-MC080 | P1 | Readiness endpoint | CLOSED | service.py, telemetry.py, tests/test_service.py |
| INV29-MC081 | P1 | Runtime version/configuration endpoint | CLOSED | service.py, tests/test_service.py |
| INV29-MC082 | P1 | Dependency-status endpoint | CLOSED | deps.py, telemetry.py, tests/test_telemetry.py |
| INV29-MC083 | P1 | Metrics implementation | CLOSED | telemetry.py, service.py, tests/test_telemetry.py |
| INV29-MC084 | P1 | Structured logging implementation | CLOSED | telemetry.py, tests/test_telemetry.py |
| INV29-MC085 | P1 | Trace-context propagation | CLOSED | telemetry.py, service.py, tests/test_telemetry.py |
| INV29-MC086 | P1 | Safe high-cardinality diagnostics | CLOSED | telemetry.py, tests/test_telemetry.py |
| INV29-MC087 | P1 | Decision-reason event stream | CLOSED | telemetry.py, admission.py, tests/test_telemetry.py |
| INV29-MC088 | P2 | Operator explain view | CLOSED | telemetry.py, tests/test_telemetry.py |
| INV29-MC089 | P1 | Release/topology correlation | CLOSED | telemetry.py, service.py, tests/test_service.py |
| INV29-MC090 | P1 | Telemetry retention/sampling/privacy/export policy | OWNER_ACTION | Retention/sampling/privacy/export policy proposed; owner ratification required. |
| INV29-MC091 | P2 | Dashboards | IMPLEMENTED_LOCAL | Dashboard definition authored; not deployed to a monitoring stack. |
| INV29-MC092 | P1 | Alerts and failure-classification rules | IMPLEMENTED_LOCAL | Alert and failure-class rules generated; not wired to an alert manager. |
| INV29-MC093 | P1 | Concrete production SLO values / support commitments | OWNER_ACTION | SLO values and support commitments proposed; owner ratification required. |
| INV29-MC094 | P1 | Canary/staged rollout procedure | IMPLEMENTED_LOCAL | Procedure defined; not exercised in a non-production estate. |
| INV29-MC095 | P1 | Supported-version compatibility matrix | IMPLEMENTED_LOCAL | Matrix published; most external cells are blocked pending labs. |
| INV29-MC096 | P1 | Patching SLA / vulnerability-response SLA / EOL policy | OWNER_ACTION | Patch/vuln-response/EOL SLAs proposed; owner + security-owner sign-off required. |
| INV29-MC097 | P1 | Detailed day-0/day-1/day-2 runbooks | IMPLEMENTED_LOCAL | Day-0/1/2 runbooks written; not yet exercised. |
| INV29-MC098 | P1 | Incident severity/paging/escalation/containment/recovery runbook | OWNER_ACTION | Severity, containment and recovery defined; paging needs a named on-call rotation. |
| INV29-MC099 | P2 | Recurring review procedure | IMPLEMENTED_LOCAL | Review procedure defined; first review not yet held. |
| INV29-MC100 | P1 | Exception/waiver/technical-debt register | CLOSED | governance/WAIVERS.json, evidence.py, tests/test_evidence.py |
| INV29-MC101 | P1 | Formal production exit-gate artifact for 4.2.0 | IMPLEMENTED_LOCAL | Formal gate artifact exists for the 4.3.0 source digest; verdict NO_GO until P0 externals close. |
| INV29-MC102 | P1 | Ownership/on-call metadata | OWNER_ACTION | Security owner, runtime owner and on-call rotation are unnamed. |
| INV29-MC103 | P1 | Change-management / release checklist | CLOSED | RELEASE_CHECKLIST.md, tools/build_release.py |

---

# Prior report (4.2.0)

# INV-29 Hybrid Wasm/unikernel — Post-Hardening Audit Report

**Audited version:** 4.2.0  
**Audit date:** 2026-09-23  
**Scope:** Files present in the supplied `inv29_hybrid_wasm_unikernel` archive only. External estate components were not available for execution.

## Executive result

The repository was parsed, corrected, hardened, and version-bumped from **4.1.0** to **4.2.0**. The highest-impact code defect was an interface-completeness mismatch: the contract and README advertised `PK_HYBRID_VERIFICATION/1`, but no public `verify()` implementation existed. Version 4.2.0 adds that API, isolates security-critical composition logic from `pk_core`, strengthens input validation and resource bounds, and adds standalone regression tests that pass both normally and under `python -O`.

The repository is **not independently production-complete as supplied**. Its 100-item checklist is primarily a requirements inventory; many production artifacts needed to prove those requirements are not present in this archive. The missing-component inventory below distinguishes external dependencies from absent local implementation/evidence.

## Changes made in 4.2.0

1. Added `model.py` as a dependency-free core containing `WasmModule`, `HostImage`, `verify()`, `compose()`, and refusal exceptions.
2. Implemented the advertised `PK_HYBRID_VERIFICATION/1` interface.
3. Added independent verification records for the unikernel layer, Wasm layer, and import closure.
4. Enforced exact integer semantics for `required_layers`; `True`/`False` can no longer pass as integers.
5. Enforced exact boolean semantics for `sealed` and `hardened`.
6. Enforced non-empty bounded names and immutable `frozenset[str]` capability collections.
7. Added capability-count and capability-length limits to prevent unbounded malformed input from reaching sorting/difference operations.
8. Added explicit supported architecture sets for host CPU and Wasm targets.
9. Preserved verification evidence inside every successful composition record.
10. Added standalone tests for success, verification schema, import refusal, loss of either layer, unsupported architectures, invalid layer counts, higher environment requirements, malformed capability sets, empty names, and input-size limits.
11. Corrected the README statement that `MASTER.md` was included; it is absent from the supplied archive.
12. Corrected the contract failure-mode wording to match what can actually be verified at this layer.

## Validation performed

- `python -m py_compile model.py component.py contract.py tests/test_model.py tests/test_component.py` — **PASS**
- `python tests/test_model.py` — **PASS (10 tests)**
- `python -O tests/test_model.py` — **PASS (10 tests)**
- `python tests/test_component.py` — **3 SKIPPED**, because the external `pk_core` package is not present in this archive.

## Remaining missing components

### A. Required external runtime / estate dependencies

1. **`pk_core` runtime package** — required by `component.py` and `contract.py`; without it, the 100-item component assessment and gate cannot execute.
2. **INV-11 Interface contract language** — required for typed signature/version compatibility checks. Without INV-11, `assess_interfaces()` intentionally reports a partial result.
3. **INV-27 Unikernel execution** — declared upstream dependency supplying a verified sealed host image; implementation/evidence is not included here.
4. **INV-44 Wasm hardening system** — declared upstream dependency supplying hardened Wasm runtime configuration; implementation/evidence is not included here.
5. **PLN-04 Execution plane** — declared downstream admission plane; not included here.
6. **INV-30 Capability hardware sandbox** — optional peer/third isolation layer; not included here.

### B. Missing source / specification artifacts referenced or implied by the repository

7. **`MASTER.md`** — explicitly referenced by the prior README as containing the 100 per-item master prompt/workflow documents, but absent from the archive.
8. **Machine-readable schema for `PK_HYBRID_COMPOSITION/1`** — the implementation emits the schema identifier, but no JSON Schema / protobuf / WIT / IDL artifact is included.
9. **Machine-readable schema for `PK_HYBRID_VERIFICATION/1`** — same gap for verification records.
10. **Typed capability/interface definitions** — local composition still reconciles imports by capability name; signature compatibility remains delegated to INV-11 rather than represented in this repository.
11. **Schema evolution / compatibility policy** — no explicit forward/backward compatibility rules, deprecation policy, or migration procedure for the two public record schemas.
12. **Formal architecture document / data-flow diagram** — responsibility is documented, but no deployable architecture/topology artifact or trust-boundary diagram is included.
13. **Dedicated threat model artifact** — threats are listed in the contract, but there is no structured threat model with assets, actors, attack paths, mitigations, residual risk, and verification mapping.

### C. Packaging, reproducibility, and supply-chain gaps

14. **`pyproject.toml` / package metadata** — no standardized build/install metadata is included.
15. **Pinned dependency manifest / lockfile** — no reproducible dependency set for `pk_core` or companion components.
16. **Supported Python-version declaration** — no machine-readable interpreter compatibility metadata.
17. **SBOM** — no CycloneDX/SPDX software bill of materials.
18. **Build provenance / attestation** — no SLSA-style provenance, signed build statement, or artifact attestation.
19. **Release signature / checksum manifest** — no cryptographic release verification artifacts.
20. **License file and notices** — no `LICENSE`, `NOTICE`, or third-party attribution file is present in this archive.
21. **Vulnerability scanning configuration/results** — no dependency/code scanning policy or retained scan evidence.
22. **Secret scanning configuration/results** — no repository-level secret scanning policy/evidence.

### D. Test and certification gaps

23. **Executable `pk_core` conformance in this archive** — existing conformance tests skip without the external package, so the claimed 100-finding gate cannot be reproduced from this archive alone.
24. **Public-interface contract tests for serialized records** — tests validate Python dictionaries but not schema files or cross-language consumers.
25. **INV-11 integration test fixture** — no local fixture or test double verifies typed signature drift when the sibling component is absent.
26. **INV-27 integration test** — no real sealed unikernel artifact is composed in tests.
27. **INV-44 integration test** — no real hardened Wasm runtime configuration/artifact is exercised.
28. **PLN-04 integration test** — no admission/placement handoff is exercised.
29. **Cross-architecture compatibility matrix/tests** — no real x86_64/aarch64 host and wasm32/wasm64 execution matrix.
30. **Hypervisor compatibility tests** — no Firecracker/KVM/Hyper-V/etc. integration evidence.
31. **Wasm runtime compatibility tests** — no Wasmtime/Wasmer/WAMR/etc. matrix.
32. **Fuzzing harness** — no fuzz target for capability sets, record decoding, schema parsing, or boundary inputs.
33. **Property-based tests** — no invariant/property tests for closure, monotonic layer requirements, or malformed records.
34. **Concurrency/race tests** — no concurrent composition/state tests; current core is stateless, but any surrounding registry/cache path is untested here.
35. **Security adversarial tests** — no dedicated suite for capability-confusion, layer downgrade, schema tampering, oversized input, or hostile names beyond the new unit cases.
36. **Benchmark suite** — no startup, composition, throughput, latency, CPU, memory, or allocation benchmark.
37. **Soak/burst/fleet-scale tests** — absent.
38. **Failure-injection / chaos tests** — no dependency loss, corrupted image, partial verification, or control-plane outage harness.
39. **Disaster / partition / reconnect tests** — absent.
40. **Machine-readable certification evidence** — no retained `evidence/` ledger or signed conformance evidence is included.
41. **Gate output artifact** — no `conformance/PK_GATE_RESULTS.json` from a successful 4.2.0 gate run is included.
42. **CI pipeline** — no workflow automatically running compile, unit, optimized-mode, conformance, lint, type, security, and packaging checks.

### E. Runtime security / policy gaps

43. **Authentication mechanism** — not implemented here; only composition semantics are present.
44. **Authorization / policy engine integration** — no executable policy determining which tenant/workload may request which host capabilities.
45. **Tenant identity binding** — contract says one tenant per composition, but the composition record carries no tenant identity.
46. **Workload identity / attestation binding** — no digest, signature, provenance, or workload identity is bound into the record.
47. **Host image identity / digest binding** — host is represented only by a name and flags, not an immutable image digest/attestation.
48. **Wasm module identity / digest binding** — module is represented only by a name and attributes, not a content digest/signature.
49. **Cryptographic verification of `sealed`** — `sealed=True` is caller-provided; there is no signature/measurement/attestation proof in this component.
50. **Cryptographic verification of `hardened`** — `hardened=True` is caller-provided; there is no signed policy result or hardening attestation.
51. **Measured-boot / TPM / confidential-compute evidence** — absent.
52. **Capability provenance** — exposed/imported capability names are not tied to policy source, version, signer, or approval.
53. **Capability denylist / dangerous-capability policy** — import closure ensures availability, not whether a capability such as raw device/network access should be forbidden.
54. **Capability cardinality policy per workload/tenant** — only a global defensive maximum now exists; no least-privilege policy budget exists.
55. **Replay protection / record freshness** — records contain no nonce, timestamp, generation, or monotonic sequence.
56. **Record integrity/signature** — composition and verification records are not signed or MAC-protected.
57. **Secure serialization/parser** — no canonical serialization format is defined; Python dicts are returned directly.
58. **Secret handling / redaction rules in code** — no local secret fields exist today, but there is no generic redaction policy for future record growth.

### F. Reliability and state-management gaps

59. **Persistence model** — no durable store for composition/verification records.
60. **Idempotency contract** — no idempotency key or duplicate-composition semantics.
61. **Lifecycle state machine** — no explicit requested/verified/composed/running/draining/failed/retired states.
62. **Reconciliation loop** — no controller that re-verifies compositions after host/module/policy changes.
63. **Revocation handling** — no behavior for revoked module signatures, host images, policies, or capabilities.
64. **Rollback implementation** — README describes rollback conceptually but no executable rollback procedure/tool is present.
65. **Emergency-disable implementation** — documented as registry removal, but no local registry operation/tool is included.
66. **Backup/restore/reconstruction implementation** — absent for any future persisted composition state.
67. **Dependency timeout/retry/circuit-breaker behavior** — not relevant to the pure model but absent from any integration/controller implementation.
68. **Partial-failure handling around external verifiers** — no orchestration layer is included.

### G. Performance and resource-efficiency gaps

69. **Baseline performance data** — none included.
70. **p50/p95/p99/worst-case thresholds** — none defined as measurable values.
71. **Load/overload measurements** — none included.
72. **Per-tenant/per-workload overhead measurements** — absent.
73. **Copy/serialization/context-switch analysis** — absent.
74. **Optimization evidence** — no zero-copy, batching, locality, caching, or kernel-bypass evaluation.
75. **Memory/concurrency/queue operational limits** — input collection bounds now exist, but no runtime service resource model exists.
76. **Power/thermal measurements** — absent.
77. **Capacity model and saturation thresholds** — absent.
78. **Performance regression gate** — absent.

### H. Observability and explainability gaps

79. **Health endpoint** — absent.
80. **Readiness endpoint** — absent.
81. **Runtime version/configuration endpoint** — absent.
82. **Dependency-status endpoint** — absent.
83. **Metrics implementation** — signals are declared in `contract.py`, but no counters/gauges/histograms are emitted by this repository.
84. **Structured logging implementation** — absent.
85. **Trace-context propagation** — absent.
86. **Safe high-cardinality diagnostics** — no implementation/policy.
87. **Decision-reason event stream** — returned records contain verification details, but there is no durable operator/audit event channel.
88. **Operator explain view** — absent.
89. **Release/topology correlation** — absent.
90. **Telemetry retention/sampling/privacy/export policy** — absent.
91. **Dashboards** — absent.
92. **Alerts and failure-classification rules** — absent.

### I. Operations, release, and governance gaps

93. **Concrete production SLO values / support commitments** — contract has zero-error logical invariants, but no availability/latency/support SLO package.
94. **Canary/staged rollout procedure** — not provided as executable runbook.
95. **Supported-version compatibility matrix** — absent.
96. **Patching SLA / vulnerability-response SLA / EOL policy** — absent.
97. **Detailed day-0/day-1/day-2 runbooks** — README gives a short outline, not an operational runbook with prerequisites, commands, rollback checks, owners, and expected evidence.
98. **Incident severity/paging/escalation/containment/recovery runbook** — absent.
99. **Recurring review procedure** — no scheduled access/policy/dependency/configuration/architecture review artifact.
100. **Exception/waiver/technical-debt register** — absent.
101. **Formal production exit-gate artifact for 4.2.0** — absent because the external gate could not be executed in the supplied isolated repository.
102. **Ownership/on-call metadata** — no CODEOWNERS, service owner, escalation contact, or support rotation artifact.
103. **Change-management / release checklist** — changelog exists, but no formal release approval checklist or evidence bundle template.

## Important residual design limitations

- The local model validates *names* of capabilities, not WIT/function signatures. Typed compatibility remains an external INV-11 responsibility.
- `sealed` and `hardened` are trusted assertions supplied by callers. Production integration should replace these booleans with verifiable signed/attested evidence and bind evidence digests into the composition record.
- Supported host/Wasm architecture sets are validation allowlists, not proof that a particular runtime build actually supports a given host/guest pairing.
- A requested `required_layers > 2` is correctly refused because this implementation only knows two layers; optional third-layer support would require a concrete layer model and verifier rather than simply raising the count.

## Post-audit status

**Core composition model:** hardened and locally testable.  
**Contract/API consistency:** improved; both advertised interfaces now exist.  
**Standalone unit validation:** PASS.  
**Full 100-item production certification:** NOT REPRODUCIBLE from this archive because `pk_core` and estate dependencies/evidence are missing.  
**Production readiness:** requires closure of the applicable missing components above and a successful external gate with retained evidence.
