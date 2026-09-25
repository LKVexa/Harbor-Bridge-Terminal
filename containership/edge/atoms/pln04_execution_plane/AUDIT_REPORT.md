# PLN-04 Execution Plane — Post-Update Audit Report

**Audited input:** 4.1.0 archive supplied on 2026-09-22  
**Updated version:** 4.2.0  
**Audit scope:** parse, correctness repair, hardening, version consistency, testability, security invariants, interface truthfulness, and post-update missing-component inventory.

## Result

The repository was upgraded to 4.2.0 and materially hardened. The dependency-free execution core is testable without `pk_core`; 13 standalone tests pass, including optimized-mode and concurrency checks. Two framework certification tests remain skipped because `pk_core` is not present in the supplied archive/environment.

This repository is **not yet a complete production execution plane**. It now makes fewer unsupported certification claims, but substantial provider, distributed-systems, security-infrastructure, observability, performance, and release-governance components remain external or absent. The inventory below lists all missing components identified by this audit.

## Defects repaired in 4.2.0

1. **False-positive checklist evidence mappings — critical.** Admission routing had been used as evidence for configuration provenance (`C036`), and teardown behavior had been used as evidence for crash consistency (`C057`). Those unrelated overrides were removed/re-mapped.
2. **Standalone tests were effectively all skipped — high.** The 4.1.0 test class was guarded entirely by `pk_core` availability. Core execution logic was split into `runtime.py`, and dependency-free tests now execute in the supplied environment.
3. **Attestation restoration could add an unsupported tier — critical.** A node configured only with `process` could previously be mutated into offering `vm` by calling restore logic on an absent tier. Attestation changes are now restricted to configured tiers.
4. **Resident workloads survived attestation loss as active — high.** Residents on a failed tier are now marked `quarantined`; new admissions fail closed.
5. **Quarantined workloads could have silently resumed conceptually — high.** Restoring tier eligibility no longer reactivates resident state; teardown/recreation is required.
6. **Re-admission could silently change isolation tier — high.** A live workload is no longer migrated in-place by `admit()` when a stronger classification requires another tier.
7. **Weaker re-admission could weaken policy metadata — high.** The stronger existing trust classification is retained.
8. **Cross-tenant teardown had no ownership check — high.** Tenant-scoped teardown validates ownership; unscoped teardown requires explicit `privileged=True`.
9. **Same-node state transitions were race-prone — high.** Runtime state is protected by a re-entrant lock; concurrent ownership of the same workload id is tested.
10. **Resident state growth was unbounded — high.** Node and per-tenant limits are enforced with `CapacityExceeded`.
11. **Input validation accepted whitespace/control-heavy identifiers — medium.** Workload and tenant ids now reject empty/whitespace-only values, ASCII control characters, and values over 256 characters.
12. **Tier attestation values accepted non-booleans — medium.** Tier-state configuration now requires real `bool` values.
13. **Expected GAP-06 refusal lacked an explicit failure branch — medium.** A non-refusal can no longer pass the probe accidentally.
14. **No tamper-evident local security event chain — high.** Security/lifecycle transitions now append to an in-memory SHA-256 hash chain.
15. **Typed interface schemas were claimed but not shipped — high.** JSON Schemas now exist for the three declared versioned interfaces.
16. **README falsely claimed `MASTER.md` was included — medium.** Documentation now states that the source master artifact is absent.
17. **Package core was unusable without `pk_core` — medium.** Core runtime symbols can now be imported and exercised without the certification dependency; the framework adapter remains optional/external.

## Validation performed

- Python byte-compilation of the complete updated package.
- `python -m unittest -v pln04_execution_plane.tests.test_component`.
- Optimized-mode runtime test via a subprocess using `python -O`.
- Strict JSON parse of `CHECKLIST.json` and all interface schemas.
- Version consistency between `VERSION` and `__version__`.
- Same-workload concurrent ownership race test.
- Cross-tenant admission and teardown refusal tests.
- Attestation failure/quarantine/restoration tests.
- Capacity ceiling tests.
- Audit-chain verification tests.

## Post-update missing-component inventory

The following are the remaining missing components identified from the updated repository and its 100-item checklist. “Missing” means the capability is not implemented or evidenced inside this archive; some are intentionally external architectural dependencies.

| ID | Missing component | Why it is still missing | Related checklist |
|---|---|---|---|
| M01 | `MASTER.md` source prompt/workflow artifact | The 4.1.0 README referenced it, but it was not present in the supplied archive and cannot be reconstructed verbatim from the repository. | C011, C020 |
| M02 | Pinned/installable `pk_core` dependency | No dependency manifest or vendored framework is present, so full checklist/gate execution cannot run standalone. | C031, C093, C094 |
| M03 | Real execution-tier provider adapter layer | `runtime.py` selects a tier and records state but does not invoke a process sandbox, Wasm runtime, unikernel, microVM, or full VM. | C021, C030, C031, C040, C083 |
| M04 | Explicit Wasm provider binding | The previous provider-backing probe omitted Wasm entirely; no concrete Wasm runtime adapter is present after hardening. | C031, C083 |
| M05 | Hardware capability discovery integration | `GAP-02` is declared upstream but no adapter converts discovered CPU/device/hypervisor capability into the node catalogue. | C003, C030, C083 |
| M06 | Hardware-rooted node/tier attestation implementation | Local tier state is boolean; the package depends on external `GAP-06` for rooted evidence. | C044, C048, C050 |
| M07 | Signed workload-classification provenance | `trust_class` is accepted as an input string; there is no signed/authorized binding to scheduler/security-plane classification. | C023, C024, C041, C046 |
| M08 | Actor authentication and capability authorization | Python functions have no authenticated caller identity/capability token enforcement at an external boundary. | C023, C024, C042 |
| M09 | Executable/policy artifact signature, digest, provenance, and allowlist verification | No image/module/kernel/policy verification occurs before a workload is admitted. | C045 |
| M10 | Actual kernel/memory/network/storage/device isolation enforcement | Admission policy is present, but concrete isolation is delegated to missing tier providers. | C043, C046, C050 |
| M11 | Durable resident/catalogue state store | Instances, catalogue status, and audit history are memory-only and disappear on restart. | C057, C095 |
| M12 | Distributed ownership fencing and duplicate-execution prevention | The lock prevents only same-process races; there is no lease, epoch, consensus, or fencing token across nodes/controllers. | C058 |
| M13 | Full provider lifecycle state machine | There is no `pending/starting/running/stopping/failed/orphaned` provider handshake with start/stop timeout, cancellation, or idempotency token. | C014, C015, C025, C026, C051 |
| M14 | Teardown failure detection, orphan reaper, and node-drain integration | Local teardown deletes state; it cannot prove provider resource destruction or escalate incomplete teardown to drain. | C051, C052, C055, C059, C060 |
| M15 | Retry/backoff/jitter and circuit-breaker implementation | No dependency call path exists yet, therefore no bounded retry or dependency circuit state exists. | C025, C053, C054 |
| M16 | Production fairness and resource-capacity model | Static count ceilings exist, but no CPU/memory/device-weighted quota, queueing fairness, or saturation prediction exists. | C017, C028, C067, C069 |
| M17 | Declarative site/environment configuration system | No versioned config document, provenance/author/activation record, atomic update, or rollback mechanism exists. | C032-C038 |
| M18 | Secret/KMS and encryption integration | No encrypted persistent state, transport security, key management, or rotation implementation exists. | C039, C047 |
| M19 | Durable/externally anchored tamper-evident audit sink | The new hash chain is in-memory only and can be lost with the process; it is not anchored to immutable storage. | C049, C073, C079 |
| M20 | Metrics, structured logs, distributed tracing, health/readiness, and explain endpoint | The contract names signals, but there is no exporter, trace propagation, readiness surface, or operator explain API. | C071-C078 |
| M21 | Telemetry retention/privacy/sampling/export policy plus dashboards and alerts | No operational telemetry policy or dashboard/alert artifacts are shipped. | C075, C079, C080 |
| M22 | Reproducible performance baselines and release regression gates | No p50/p95/p99/worst-case benchmark suite, resource-overhead baseline, power test, or automated regression threshold exists. | C061-C070 |
| M23 | Fuzz/property testing of untrusted inputs and schemas | Current tests are deterministic unit/concurrency cases only; no fuzz harness/corpus is present. | C085 |
| M24 | Integration tests against every execution tier/provider | No real process/Wasm/unikernel/microVM/full-VM provider integration suite is present. | C030, C083 |
| M25 | CPU/runtime/hypervisor/protocol compatibility matrix and tests | No x86/ARM, hypervisor, runtime, provider, or cross-version compatibility test matrix exists. | C027, C084, C093 |
| M26 | Fault-injection, partition, reconnect, and disaster tests | No provider crash, node loss, network partition, stale-control-plane, or reconnect fault suite is present. | C060, C089 |
| M27 | Soak, burst, overload, scale, and fleet-scale tests | No sustained load or fleet simulation harness exists. | C063, C088 |
| M28 | CI production gate and machine-readable acceptance evidence | No CI workflow, generated acceptance bundle, `PK_GATE_RESULTS.json`, signed evidence package, or release-blocking pipeline is included. | C090, C100 |
| M29 | Supply-chain bill of materials and dependency vulnerability scanning | No SBOM, provenance attestation, dependency lock, scanner config, or signed release manifest exists. | C041, C045, C094 |
| M30 | Canary/staged rollout and automated rollback/emergency-disable implementation | README describes operational intent, but no deploy controller or executable rollout/rollback automation is shipped. | C092 |
| M31 | Backup/restore/migration/reconstruction implementation and tests | Memory-only state has no snapshot, restore, migration, or reconstruction procedure. | C095 |
| M32 | Accountable owner, on-call escalation, and incident-response runbook | No named ownership metadata, pager path, severity model, containment playbook, or recovery procedure exists. | C009, C097 |
| M33 | Patch/EOL SLA, recurring-review process, and waiver/debt registry | No lifecycle policy, review cadence artifact, exception owner/expiry registry, or deprecated-behavior ledger exists. | C094, C098, C099 |
| M34 | Concrete RPC/WIT/HTTP transport handlers | JSON Schemas now define envelopes, but no transport/server/client implementation exposes them. | C021-C030 |
| M35 | Runtime validation/serialization against the shipped schemas | The Python runtime does not yet parse or validate `PK_ADMISSION/1`, catalogue, or lifecycle JSON envelopes. | C022, C026, C029 |
| M36 | External lifecycle/event export adapter | Local `AuditEvent` records are not yet transformed/published as `PK_TIER_LIFECYCLE/1` or sent to observability systems. | C021, C049, C072-C074 |
| M37 | Attestation freshness, expiry, nonce binding, replay protection, and trusted-time policy | The local catalogue contains only current booleans; attestation epochs/evidence validity are not enforced by this package. | C044, C048, C050 |
| M38 | Site/residency-aware policy enforcement | Site/environment boundary text exists, but admission does not consume residency/topology/site constraints. | C012, C019, C055 |
| M39 | Side-channel/co-residency mitigation policy | Threats mention side channels, but there is no SMT/cache/NUMA/co-residency policy or enforcement integration. | C041, C043, C046, C050 |
| M40 | Provider resource zeroization and reuse proof | Local teardown removes a record but cannot verify memory/device/storage zeroization before reuse. | C046, C051, C060 |
| M41 | Approved architecture decision record | No approved ADR establishes the tier order, trust-class mapping, provider choices, and exception policy. | C010 |
| M42 | Formal requirements traceability matrix | `CHECKLIST.json` lists requirements, but there is no complete requirement → implementation → test/evidence matrix independent of `pk_core`. | C020 |
| M43 | Formal error-code taxonomy and retryability contract | Python exception classes exist, but stable machine-readable error codes/details and retryability semantics are not implemented at a public interface. | C014, C026 |
| M44 | Admission latency instrumentation and SLO measurement | `admission_seconds` is declared in the contract, but no timer/histogram exporter or SLO measurement implementation exists. | C013, C061, C062, C072, C091 |
| M45 | Production-grade queue/backpressure model | Admission is synchronous and local; there is no bounded request queue, cancellation propagation, or backpressure protocol. | C025, C028, C054, C067 |
| M46 | Release/build/install metadata and dependency lock | No `pyproject.toml`, lockfile, reproducible build recipe, or package-install metadata is present. | C031, C070, C094 |
| M47 | License/NOTICE provenance artifact | The archive contains no license or notice file, so redistribution/legal provenance is unspecified at repository level. | Governance/repository completeness |
| M48 | Full external-framework re-certification evidence | Because `pk_core` is absent, the updated component's 100-item framework assessment and gate have not been executed after these changes. | C090, C100 |

## Important interpretation notes

- The new local audit chain is a **tamper-evident data structure**, not a durable security log. Without external anchoring/persistence it must not be treated as sufficient evidence for production non-repudiation.
- The new JSON Schemas are **contract definitions**, not implemented network endpoints. They reduce interface ambiguity but do not satisfy authentication, authorization, transport, compatibility, timeout, or backpressure requirements by themselves.
- The new capacity limits are **safety bounds**, not a validated production capacity model.
- `Node.restore_attestation()` is intentionally a trusted control-plane operation. Until M06/M08/M37 are implemented, the caller remains part of the trusted computing base.
- The repository should not claim all 100 checklist requirements are satisfied until M48 can be run with the actual `pk_core` framework and the remaining partial/missing components are resolved or formally accepted as external dependencies.


---

# 4.3.0 remediation addendum (2026-09-23)

Input: the 4.2.0 package plus `PLN04_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (M01–M48). Per-item status, implementation, tests and residuals are in `docs/TRACEABILITY.md` / `traceability/rtm.json`.

**Outcome:** 23 PRESENT, 22 PARTIAL, 3 BLOCKED (M02 pk_core, M47 licence, M48 external re-certification). Every PARTIAL names the external dependency or human approval its acceptance gate still needs. The release gate is **NO_GO**. That verdict is correct and stays until the owner supplies those inputs.

The new code has not been independently security-reviewed. Owner and security reviewer are UNASSIGNED.
