# INV-43 repository audit report

**Updated version:** 4.3.0
**Audit date:** 2026-09-22
**Workflow executed:** `remediation/INV43_v4.2.0_MISSING_COMPONENT_REMEDIATION_CHECKLIST.md` (52 items)
**Local production gate:** **NO_GO** — `conformance/INV43_LOCAL_GATE.json` (no approver exists; pk_core absent; governance blockers open)

## 4.3.0 executive result

All 52 components were worked. 21 are implemented in-repository with positive and negative tests (LOCAL_IMPLEMENTED), 27 have their in-repository part implemented but name an external or human dependency that is still missing (PARTIAL), and 4 cannot be done inside this repository at all (BLOCKED: the original `MASTER.md`, `pk_core`, an accountable owner, and a license decision). No item is claimed complete: the checklist requires independent reproduction and an approved gate, and this pass is not an independent reviewer of its own work.

Verification (all recorded in `evidence/verification/`):
- `python -B verify.py` — PASS, 125 tests, 2 skipped (the two `pk_core` adapter tests), jsonschema required.
- `python -B -O verify.py` — PASS, same counts.
- `PK_REQUIRE_CORE=1 python -B verify.py` — **FAILS AS DESIGNED** (exit 4): `pk_core` is absent.
- `tools/verify_governance.py` — consistent; 21 open production blockers. `--strict` exits 1.
- `bench/run_bench.py --gate` — all six metrics `met_under_proposed_threshold`; overall `NOT_CERTIFIED_THRESHOLDS_UNAPPROVED`.
- `tools/verify_release.py` — SHA256SUMS, provenance subject, Ed25519 signature (ephemeral dev key), evidence ledger chain and anchored head all intact.

Seven defects in this pass's own work were caught by its tests/benchmark and fixed (listed in `CHANGELOG.md`). One real-host finding: the build host reports `spectre_v2 … BHI: Vulnerable`, which INV-43 now classifies as inactive and refuses cross-tenant co-tenancy on (`evidence/host_readback.json`).

## 4.3.0 remediation status (from `remediation/STATUS.json`)

| # | Sev | Component | State | Still missing |
|---:|:--|:--|:--|:--|
| 01 | BLOCKER | Original `MASTER.md` / master-prompt provenance artifact | **BLOCKED** | original MASTER.md (not in any supplied source); approval of EXC-001 by accountable owner (governance/OWNERS.json is unassigned) |
| 02 | BLOCKER | `pk_core` runtime source/package plus an approved version pin | **BLOCKED** | pk_core package + approved pin |
| 03 | BLOCKER | Machine-readable conformance/evidence outputs (`evidence/`, `conformance/`, sealed gate result) | **PARTIAL** | pk_core gate output (item 02); independent reproduction |
| 04 | HIGH | Reproducible package/build metadata (`pyproject.toml` or equivalent), dependency lock, and supported Python declaration | **LOCAL_IMPLEMENTED** | wheel hashes in the lock (item 23) |
| 05 | HIGH | Approved architecture decision record for transient-execution defense | **PARTIAL** | ADR approval by accountable owner (governance/OWNERS.json is unassigned) |
| 06 | HIGH | Resolution of the checklist's **Software Fault Isolation (SFI)** requirement versus the implemented mitigation-state/co-tenancy model | **PARTIAL** | PLN-04 SFI ADR; approval by accountable owner (governance/OWNERS.json is unassigned) |
| 07 | HIGH | Accountable owner, escalation path, support commitment, and on-call responsibility | **BLOCKED** | named owner, team, on-call, escalation |
| 08 | HIGH | Requirements traceability matrix from all 100 requirements to concrete implementation and verification evidence | **LOCAL_IMPLEMENTED** | — |
| 09 | BLOCKER | Hardware/kernel/microcode mitigation read-back collector | **PARTIAL** | core-scheduling observability (per-task prctl state lives in SCH-01); non-Linux read-back sources |
| 10 | HIGH | Freshness/evidence metadata for node observations (source, timestamp/monotonic age, collector identity, stale-data TTL) | **LOCAL_IMPLEMENTED** | — |
| 11 | BLOCKER | Node/collector authentication or attestation chain | **PARTIAL** | hardware-rooted attestation (TPM/SEV-SNP/TDX) service |
| 12 | HIGH | Authorization and least-privilege capability model for recording/querying posture | **LOCAL_IMPLEMENTED** | identity-provider binding for principals |
| 13 | HIGH | Workload trust-class policy source and authoritative mapping to required mitigations | **PARTIAL** | policy content approval by a policy owner |
| 14 | HIGH | Declarative configuration format, schema, secure defaults, site/environment overrides, provenance, activation transaction, and rollback | **LOCAL_IMPLEMENTED** | — |
| 15 | HIGH | Scheduler/placement integration adapter and refusal propagation | **PARTIAL** | SCH-01 implementation to integrate against |
| 16 | HIGH | Hardware capability discovery integration (`GAP-02`) | **PARTIAL** | GAP-02 implementation / real capability records |
| 17 | HIGH | Execution-plane / isolation-tier integration (`PLN-04`) | **PARTIAL** | PLN-04 implementation |
| 18 | MEDIUM | Legacy CPU expansion-path peer integration (`INV-34`) | **PARTIAL** | INV-34 implementation |
| 19 | HIGH | Explicit external API/RPC/WIT/event/control-plane transport, if this component is intended to run as a service | **PARTIAL** | TLS certificate issuance/rotation (deployment) |
| 20 | MEDIUM | Interface version negotiation and backward/forward compatibility tests | **LOCAL_IMPLEMENTED** | — |
| 21 | MEDIUM | Full schema-conformance test runner using a standards validator | **LOCAL_IMPLEMENTED** | — |
| 22 | HIGH | Tamper-evident security audit log / append-only event chain | **PARTIAL** | WORM/remote retention sink |
| 23 | HIGH | Supply-chain integrity package: SBOM, artifact digest/signature, provenance/attestation, approved dependency policy | **PARTIAL** | release signing key (current signature is an ephemeral dev key); approved dependency policy |
| 24 | MEDIUM | Formal threat-model document covering malicious tenants, compromised workloads, hostile inputs, supply chain, and control-plane abuse | **PARTIAL** | independent security review |
| 25 | HIGH | Adversarial security test suite (privilege escalation, injection, replay, spoofing, escape, side-channel misuse, exhaustion) | **LOCAL_IMPLEMENTED** | — |
| 26 | HIGH | Fuzzing/property-based testing for identifiers, schemas, required-set handling, and untrusted boundary inputs | **LOCAL_IMPLEMENTED** | coverage-guided fuzzing infrastructure (optional) |
| 27 | HIGH | Concurrency model, synchronization/thread-safety guarantee, and race tests | **LOCAL_IMPLEMENTED** | — |
| 28 | HIGH | Failure taxonomy plus health/stall detection | **LOCAL_IMPLEMENTED** | — |
| 29 | MEDIUM | Retry/backoff/jitter policy for future read-back/control-plane operations | **LOCAL_IMPLEMENTED** | — |
| 30 | HIGH | Admission control, load shedding/circuit breaking, and bounded resource model | **LOCAL_IMPLEMENTED** | — |
| 31 | HIGH | Failover/degraded/restart/replay/split-brain semantics | **PARTIAL** | multi-replica HA (declared unsupported) |
| 32 | HIGH | Quarantine/freeze/disable/emergency-control implementation | **LOCAL_IMPLEMENTED** | — |
| 33 | HIGH | Fault-injection and disaster/partition/reconnect tests | **PARTIAL** | real network-partition / disaster lab |
| 34 | HIGH | Reproducible performance benchmark harness and measured baseline | **PARTIAL** | per-mitigation cost attribution via A/B boots on target hardware |
| 35 | HIGH | Approved p50/p95/p99/worst-case thresholds plus performance-regression release gate | **PARTIAL** | threshold approval by accountable owner (governance/OWNERS.json is unassigned) |
| 36 | MEDIUM | CPU/memory/storage/network/power/thermal capacity model, including edge-node measurements | **PARTIAL** | power/thermal and edge-node measurements |
| 37 | HIGH | Runtime metrics emitter for rate/errors/latency/saturation/backlog/resources | **LOCAL_IMPLEMENTED** | — |
| 38 | HIGH | Structured logs with stable node/tenant/workload/operation IDs and redaction/privacy policy | **LOCAL_IMPLEMENTED** | — |
| 39 | MEDIUM | Distributed trace propagation/correlation | **LOCAL_IMPLEMENTED** | — |
| 40 | MEDIUM | Operator explain surface linking a decision to inputs, policy, topology, and release lineage | **LOCAL_IMPLEMENTED** | — |
| 41 | MEDIUM | Dashboards and alerts separating load, degradation, policy rejection, dependency failure, attack, and software defect | **PARTIAL** | deployment and validation on live monitoring |
| 42 | HIGH | Integration tests with all supported adjacent layers | **PARTIAL** | real SCH-01/GAP-02/PLN-04/INV-34 components |
| 43 | HIGH | Compatibility test matrix across supported CPU architectures, kernels/runtimes, hypervisors, providers, and protocol versions | **PARTIAL** | hypervisor/provider/kernel lab runs |
| 44 | MEDIUM | Soak, burst, overload, scale-out/scale-in, and fleet-scale tests | **PARTIAL** | fleet-scale soak environment |
| 45 | MEDIUM | Canary/staged rollout implementation and rollback automation | **LOCAL_IMPLEMENTED** | approver identity verification (platform IdP) |
| 46 | MEDIUM | Backup/restore/migration/reconstruction decision and procedure | **LOCAL_IMPLEMENTED** | — |
| 47 | MEDIUM | Complete day-0/day-1/day-2 runbook with dependency checks and failure procedures | **PARTIAL** | on-call names (accountable owner (governance/OWNERS.json is unassigned)) |
| 48 | HIGH | Incident response plan: severity model, paging, containment, recovery, post-incident evidence | **PARTIAL** | paging targets (accountable owner (governance/OWNERS.json is unassigned)) |
| 49 | MEDIUM | Recurring access/policy/dependency/configuration/architecture review schedule and evidence | **PARTIAL** | reviews actually held and recorded |
| 50 | MEDIUM | Exception/waiver/technical-debt/deprecation ledger with owners and expirations | **LOCAL_IMPLEMENTED** | approval of each PROPOSED entry |
| 51 | HIGH | Vulnerability response, patching, and end-of-life SLA | **PARTIAL** | security contact and SLA approval (accountable owner (governance/OWNERS.json is unassigned)) |
| 52 | MEDIUM | Licensing/NOTICE metadata for redistribution | **BLOCKED** | license decision by accountable owner (governance/OWNERS.json is unassigned) |

Traceability: `TRACEABILITY.json` maps all 100 checklist controls to remediation items and evidence (44 LOCAL_IMPLEMENTED, 45 PARTIAL, 11 BLOCKED at control level).

## What would move the gate
1. Fill `governance/OWNERS.json`; that unblocks approvals of ADR-0001/0002, the policy, perf thresholds, EXC-001..004, SECURITY.md contacts, runbook/IR paging.
2. Supply `pk_core` and pin it in `deps/pk_core.lock.json`; rerun with `PK_REQUIRE_CORE=1`.
3. Choose and package a license (`LICENSE`, `NOTICE`, `pyproject.toml`).
4. Sign the release with a real release key; add wheel hashes to the dev lock.
5. Lab work: per-mitigation A/B cost on target hardware, hypervisor/provider matrix, fleet soak, partition drills, power/thermal on edge nodes, hardware-rooted attestation, and integration against real SCH-01/GAP-02/PLN-04/INV-34.
6. Independent review of everything above; then record GO with approver identity in the gate.

---

## Historical record: 4.2.0 audit (retained unchanged)

**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** the supplied `inv43_transient_execution_defense` archive only. A component listed as missing below may exist elsewhere in the larger platform; it is reported because it is not present or independently verifiable in this distribution.

## Executive result

The supplied 4.1.0 package was syntactically valid but could report a green test run while all three tests were skipped when `pk_core` was absent. It also exposed a `PK_MITIGATIONS/1` status contract that did not contain the promised per-mitigation status/cost records, referenced a nonexistent `MASTER.md`, accepted several malformed inputs, and had no local typed interface schemas.

Version 4.2.0 fixes those repository-local defects. The core policy model is now independently importable/testable, failures are machine-readable, the externally visible local data shapes have schemas/fixtures, and release CI can require the external registry dependency instead of silently skipping it.

This is **not yet a complete production implementation or production certification package**. The remaining components below are the complete set identifiable from the supplied repository plus its own 100-item checklist.

## Fixed in 4.2.0

1. Split the policy model from the optional `pk_core` adapter so local security logic can be tested without external runtime availability.
2. Added strict node/tenant/mitigation identifier validation and boolean posture validation.
3. Revalidated caller-supplied initial mitigation maps instead of trusting pre-populated state.
4. Rejected boolean, NaN, infinite, negative, zero-active, and stale nonzero inactive/unknown costs.
5. Added caller-selectable required mitigation sets and fail-closed behavior for unknown future requirements.
6. Added stable refusal codes and `PK_ERROR/1` serialization.
7. Corrected `PK_MITIGATIONS/1` to include each mitigation's status and measured cost.
8. Added Draft 2020-12 schemas and reference fixtures for status, co-tenancy, and error contracts.
9. Added standalone tests, optimized-mode verification, compile checks, and a Windows verification launcher.
10. Added strict `PK_REQUIRE_CORE=1` behavior so release CI cannot certify with a missing `pk_core` dependency.
11. Removed the false claim that `MASTER.md` is present.
12. Bumped all repository-local version pins from 4.1.0 to 4.2.0.

## Verification performed

- `python verify.py` — **PASS**: 15 tests discovered; 13 executed/passed; 2 external `pk_core` tests skipped because the dependency is absent.
- `python -O verify.py` — **PASS** with the same result, proving runtime checks do not depend on stripped `assert` statements.
- `PK_REQUIRE_CORE=1 python verify.py` — **FAILS AS DESIGNED** because `pk_core` is absent from the supplied repository/environment. This is a release-blocking dependency signal, not a regression in the standalone model.
- `python -m compileall` — **PASS**.
- Draft 2020-12 schema validation with `jsonschema` 4.26.0 — **PASS** for all three bundled reference fixtures.

## Remaining missing components

| # | Severity | Missing component / evidence | Related checklist items | Why it remains missing |
|---:|:--|:--|:--|:--|
| 1 | BLOCKER | Original `MASTER.md` / master-prompt provenance artifact | C020, C045, C090, C100 | The 4.1.0 README claimed it existed, but it was not in the archive. 4.2.0 does not fabricate it. |
| 2 | BLOCKER | `pk_core` runtime source/package plus an approved version pin | C016, C027, C031, C093, C100 | Registry contract/gate behavior cannot be executed or certified from this archive alone. |
| 3 | BLOCKER | Machine-readable conformance/evidence outputs (`evidence/`, `conformance/`, sealed gate result) | C020, C090, C100 | README shows external commands, but no resulting evidence ledger or gate artifact is supplied. |
| 4 | HIGH | Reproducible package/build metadata (`pyproject.toml` or equivalent), dependency lock, and supported Python declaration | C016, C031, C032, C040, C045 | The package is source-only; installation and dependency resolution are not reproducibly specified. |
| 5 | HIGH | Approved architecture decision record for transient-execution defense | C010 | No approved ADR is present. |
| 6 | HIGH | Resolution of the checklist's **Software Fault Isolation (SFI)** requirement versus the implemented mitigation-state/co-tenancy model | C010, C031 | The checklist explicitly names SFI, but the repository neither implements nor pins an SFI technology/specification. SFI should not be implicitly treated as equivalent to CPU transient-execution mitigations. |
| 7 | HIGH | Accountable owner, escalation path, support commitment, and on-call responsibility | C009, C091, C097 | No owner/team/contact/escalation artifact is supplied. |
| 8 | HIGH | Requirements traceability matrix from all 100 requirements to concrete implementation and verification evidence | C020 | `CHECKLIST.json` contains requirements only; it is not a bidirectional evidence map. |
| 9 | BLOCKER | Hardware/kernel/microcode mitigation read-back collector | C004, C021, C029, C030, C040 | `MitigationState.record()` receives caller-supplied state; it does not collect authoritative node read-back itself. |
| 10 | HIGH | Freshness/evidence metadata for node observations (source, timestamp/monotonic age, collector identity, stale-data TTL) | C004, C014, C015, C018, C036, C057, C071 | The model stores status/cost but cannot prove when, where, or by whom the read-back was observed. |
| 11 | BLOCKER | Node/collector authentication or attestation chain | C023, C044, C048 | A caller can supply mitigation state; no node identity/attestation validation exists in this package. |
| 12 | HIGH | Authorization and least-privilege capability model for recording/querying posture | C024, C042, C043 | No identities, roles, capabilities, or authority checks are implemented. |
| 13 | HIGH | Workload trust-class policy source and authoritative mapping to required mitigations | C006, C011, C019, C046 | 4.2.0 can evaluate a caller-provided required set, but it does not own or validate the policy that derives that set from workload trust class. |
| 14 | HIGH | Declarative configuration format, schema, secure defaults, site/environment overrides, provenance, activation transaction, and rollback | C033-C038 | No configuration subsystem or configuration provenance exists. |
| 15 | HIGH | Scheduler/placement integration adapter and refusal propagation | C003, C021, C030, C083 | `SCH-01` is named in the contract, but no integration code or integration test is present. |
| 16 | HIGH | Hardware capability discovery integration (`GAP-02`) | C003, C021, C030, C083 | Dependency is documented only; no adapter/fixture proves interoperability. |
| 17 | HIGH | Execution-plane / isolation-tier integration (`PLN-04`) | C003, C021, C030, C083 | Dependency is documented only; there is no tier-to-required-mitigation mapping or integration test. |
| 18 | MEDIUM | Legacy CPU expansion-path peer integration (`INV-34`) | C003, C030, C083 | The peer relationship is declared but not exercised. |
| 19 | HIGH | Explicit external API/RPC/WIT/event/control-plane transport, if this component is intended to run as a service | C021-C028 | Current implementation is an in-process Python library. Authn/authz, timeout, cancellation, retry, idempotency, backpressure, payload and connection limits are therefore not implemented at a transport boundary. |
| 20 | MEDIUM | Interface version negotiation and backward/forward compatibility tests | C016, C027, C093 | Schemas are versioned, but negotiation rules and compatibility tests are absent. |
| 21 | MEDIUM | Full schema-conformance test runner using a standards validator | C022, C029, C082 | Schemas and fixtures are present, but repository tests only guarantee JSON parseability/shape metadata without declaring a JSON Schema validator dependency. |
| 22 | HIGH | Tamper-evident security audit log / append-only event chain | C049 | No audit-event implementation, signature/hash chain, sink, or retention mechanism exists. |
| 23 | HIGH | Supply-chain integrity package: SBOM, artifact digest/signature, provenance/attestation, approved dependency policy | C045 | No SBOM, signature, or provenance/attestation artifacts are present; 4.2.0 includes only an unsigned SHA-256 file manifest. |
| 24 | MEDIUM | Formal threat-model document covering malicious tenants, compromised workloads, hostile inputs, supply chain, and control-plane abuse | C041 | `contract.py` lists several threats, but not a complete threat model with assets, trust boundaries, assumptions, mitigations, and residual risk. |
| 25 | HIGH | Adversarial security test suite (privilege escalation, injection, replay, spoofing, escape, side-channel misuse, exhaustion) | C050, C087 | Current negative tests cover policy input/refusal logic only. |
| 26 | HIGH | Fuzzing/property-based testing for identifiers, schemas, required-set handling, and untrusted boundary inputs | C085 | No fuzz harness/corpus/property suite is included. |
| 27 | HIGH | Concurrency model, synchronization/thread-safety guarantee, and race tests | C086 | `MitigationState` is mutable and unsynchronized; no single-thread-only contract or concurrency protection is documented/tested. |
| 28 | HIGH | Failure taxonomy plus health/stall detection | C051, C052, C071 | There is no health/readiness state machine or dependency-stall detector. |
| 29 | MEDIUM | Retry/backoff/jitter policy for future read-back/control-plane operations | C025, C053 | No dependency I/O exists yet, so retry semantics remain unspecified. |
| 30 | HIGH | Admission control, load shedding/circuit breaking, and bounded resource model | C017, C054, C067, C069 | No queue/concurrency/fan-out limits or saturation model exists. |
| 31 | HIGH | Failover/degraded/restart/replay/split-brain semantics | C014, C018, C055-C058 | The in-memory model has no distributed lifecycle or documented stateless-reconstruction contract. |
| 32 | HIGH | Quarantine/freeze/disable/emergency-control implementation | C059, C092 | Policy refusal exists, but no operator control plane for quarantining unsafe nodes or globally disabling placement is supplied. |
| 33 | HIGH | Fault-injection and disaster/partition/reconnect tests | C060, C089 | No chaos/fault harness or recovery-objective evidence exists. |
| 34 | HIGH | Reproducible performance benchmark harness and measured baseline | C061, C063, C064, C088 | Cost values are caller-provided; the repository does not measure mitigation overhead itself. |
| 35 | HIGH | Approved p50/p95/p99/worst-case thresholds plus performance-regression release gate | C062, C070 | No threshold file, benchmark history, or regression gate is present. |
| 36 | MEDIUM | CPU/memory/storage/network/power/thermal capacity model, including edge-node measurements | C061, C067-C069 | No resource or power/thermal measurement suite is supplied. |
| 37 | HIGH | Runtime metrics emitter for rate/errors/latency/saturation/backlog/resources | C071, C072 | Contract names signals but no metrics backend/exporter exists. |
| 38 | HIGH | Structured logs with stable node/tenant/workload/operation IDs and redaction/privacy policy | C073, C075, C079 | No logging implementation or telemetry policy exists. |
| 39 | MEDIUM | Distributed trace propagation/correlation | C074, C078 | No trace-context support exists. |
| 40 | MEDIUM | Operator explain surface linking a decision to inputs, policy, topology, and release lineage | C076-C078 | Errors now contain reasons, but there is no operator-facing explain endpoint/view or infrastructure/release correlation. |
| 41 | MEDIUM | Dashboards and alerts separating load, degradation, policy rejection, dependency failure, attack, and software defect | C080 | No dashboard/alert definitions are supplied. |
| 42 | HIGH | Integration tests with all supported adjacent layers | C030, C083 | Only local unit/conformance adapter tests exist. |
| 43 | HIGH | Compatibility test matrix across supported CPU architectures, kernels/runtimes, hypervisors, providers, and protocol versions | C084, C093 | No supported-platform matrix or compatibility lab evidence is present. |
| 44 | MEDIUM | Soak, burst, overload, scale-out/scale-in, and fleet-scale tests | C063, C088 | No load/fleet harness is supplied. |
| 45 | MEDIUM | Canary/staged rollout implementation and rollback automation | C038, C092 | README contains brief operational guidance only; no rollout/rollback tooling is present. |
| 46 | MEDIUM | Backup/restore/migration/reconstruction decision and procedure | C095 | Current state is in memory. The repo needs either a formal stateless-reconstruction procedure or persistent-state recovery tooling. |
| 47 | MEDIUM | Complete day-0/day-1/day-2 runbook with dependency checks and failure procedures | C096 | README is a minimal outline, not an operational runbook. |
| 48 | HIGH | Incident response plan: severity model, paging, containment, recovery, post-incident evidence | C097 | No incident runbook is present. |
| 49 | MEDIUM | Recurring access/policy/dependency/configuration/architecture review schedule and evidence | C098 | No review cadence, owner, or recorded review artifact is supplied. |
| 50 | MEDIUM | Exception/waiver/technical-debt/deprecation ledger with owners and expirations | C099 | No exception ledger is present. |
| 51 | HIGH | Vulnerability response, patching, and end-of-life SLA | C094 | No SECURITY/patch/EOL policy is supplied. |
| 52 | MEDIUM | Licensing/NOTICE metadata for redistribution | Outside the 100-item checklist | No license file or redistribution terms are included in the supplied archive. |

## Checklist interpretation notes

- The repository now has stronger local evidence for parts of C022, C026, C029, C034, C046, C076, C081, and C082, but this does not substitute for the external integration and operational evidence required elsewhere.
- C047 (encryption/key rotation) is not automatically an implementation requirement for the current in-process, non-persistent model. If a remote API, persistence, audit sink, or sensitive telemetry is added, transport/storage encryption and managed key rotation become applicable and must be supplied. Until the architecture records that applicability decision, it remains uncertified rather than assumed satisfied.
- C039 (credentials/secrets) is presently low-surface because this repository contains no credentials or secret-handling subsystem. A production integration still needs an explicit secret-handling policy and tests proving ordinary diagnostics cannot leak secret material.
- The generic 100-finding behavior of the external `pk_core` adapter cannot be treated as proof that physical artifacts above exist. Production certification should require artifact-backed evidence for each applicable checklist item.

## Release disposition

**4.2.0 is suitable as a hardened standalone policy-model/reference component, not as a self-contained production-ready transient-execution defense service.** A production gate should remain closed until the BLOCKER/HIGH items applicable to the deployed architecture are supplied and the external `pk_core` gate runs under `PK_REQUIRE_CORE=1` with retained machine-readable evidence.
