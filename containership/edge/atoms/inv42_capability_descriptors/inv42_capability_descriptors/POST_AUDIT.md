> **4.3.0 addendum (2026-09-22):** The 42 components below have been remediated. `REMEDIATION_STATUS.md` gives the per-component status. Summary:
>
> - 28 are implemented.
> - 6 are implemented but still need external run evidence.
> - 4 are implemented but blocked on owner- or platform-supplied inputs (W-001, W-004, W-005).
> - 3 are partial, with the remainder waived.
> - 1 is waived (MASTER.md).
>
> The exit gate verdict is `NOT_ELIGIBLE`. The text below is the original 4.2.0 audit and is kept for traceability.

# Post-update audit — INV-42 Capability descriptors

**Audited version:** 4.2.0  
**Audit date:** 2026-09-22  
**Baseline:** `CHECKLIST.json` (100 requirements)  
**Result:** runtime security defects fixed; repository is **not production-certifiable as a standalone archive** because required external framework/evidence and multiple production components remain absent.

## Verification performed

- Python syntax/bytecode compilation of the updated repository.
- Standalone stdlib unit/security suite under Python 3.13.5.
- Optimized-mode (`python -O`) security regression path.
- Concurrency uniqueness test (800 parallel allocations).
- Strict wire tamper/forgery/replay/foreign-table/type/fork/capacity/destroy tests.
- Static inspection for dangerous primitives and documentation/file-reference consistency.
- Second pass against all 100 checklist requirements.

## Checklist disposition

- **Met in this archive:** 31
- **Partial:** 25
- **Missing:** 35
- **Not applicable or requires formal waiver:** 9

A `met` classification here means this archive contains direct implementation/documentation/test evidence for the requirement; it does **not** substitute for the suite-level `pk_core` production gate.

## Missing production components

### MC-001 — pk_core dependency and executable suite-level release gate [BLOCKER]
**Related:** INV-42-C040, INV-42-C090, INV-42-C100  
pk_core is not bundled or declared by this archive. The three framework conformance tests therefore skip; production certification cannot be reproduced from this repository alone.

### MC-002 — MASTER.md source/master prompt artifact [HIGH]
**Related:** INV-42-C020, INV-42-C098  
README 4.1.0 claimed this file was carried verbatim, but the archive does not contain it. 4.2.0 corrects the claim but cannot reconstruct a verbatim missing source artifact.

### MC-003 — accountable owner and escalation metadata [HIGH]
**Related:** INV-42-C009, INV-42-C097  
No owner, on-call, escalation target, or support contact is present.

### MC-004 — requirements traceability matrix [HIGH]
**Related:** INV-42-C011, INV-42-C020, INV-42-C090  
No machine-readable mapping from every checklist requirement to concrete code/test/evidence exists. The component adapter exercises selected items only.

### MC-005 — adjacent-layer adapters and integration tests [HIGH]
**Related:** INV-42-C030, INV-42-C083, INV-42-C089  
No tests exercise INV-41, INV-13, INV-11, PLN-03, real ABI/WIT boundaries, process transfer, reconnect, or degraded control plane behavior.

### MC-006 — pinned implementation/specification manifest [HIGH]
**Related:** INV-42-C031, INV-42-C093  
Scoped descriptors/file descriptors, sockets, WIT imports, pk_core, and related protocol/runtime versions are not pinned in a dependency/specification manifest.

### MC-007 — reproducible packaging and dependency metadata [HIGH]
**Related:** INV-42-C031, INV-42-C040, INV-42-C093  
No pyproject/setup/lock/environment manifest defines installation, Python bounds, or the pk_core dependency. Compatibility is documented but not enforced.

### MC-008 — CI pipeline and mandatory release checks [HIGH]
**Related:** INV-42-C070, INV-42-C090, INV-42-C098, INV-42-C100  
No CI workflow runs unit, optimized-mode, integration, fuzz, benchmark, security, coverage, or pk_core gates on change/release.

### MC-009 — license and notice files [MEDIUM]
**Related:** INV-42-C094, INV-42-C100  
This archive contains no LICENSE/NOTICE, so distribution terms are not self-contained.

### MC-010 — formal success/degraded/retryable/terminal failure taxonomy [HIGH]
**Related:** INV-42-C014, INV-42-C025, INV-42-C051  
Typed local exceptions exist, but end-to-end operation outcomes, retryability, cancellation, timeout, and backpressure semantics are not specified.

### MC-011 — deployment-context semantics [MEDIUM]
**Related:** INV-42-C012, INV-42-C018, INV-42-C019  
Cloud/datacenter/near-edge/far-edge applicability, disconnected behavior, and precedence among security/residency/SLO/cost constraints are not defined.

### MC-012 — quantitative non-functional requirements [MEDIUM]
**Related:** INV-42-C013, INV-42-C062, INV-42-C091  
Zero-error security SLOs are declared, but latency, availability, determinism, throughput, support, and tail-latency thresholds are not quantified.

### MC-013 — configuration applicability/provenance decision [MEDIUM]
**Related:** INV-42-C035, INV-42-C036, INV-42-C037, INV-42-C038  
The runtime has almost no mutable configuration, but the repository does not formally mark these configuration requirements N/A or define provenance/atomic rollback if configuration is later introduced.

### MC-014 — artifact integrity, provenance, SBOM, and release signing [BLOCKER]
**Related:** INV-42-C045, INV-42-C094, INV-42-C100  
No hashes/provenance attestations, SBOM, dependency verification, signed release manifest, or approved-version policy is included.

### MC-015 — confidential authenticated transport profile [BLOCKER]
**Related:** INV-42-C023, INV-42-C044, INV-42-C047  
PK_DESCRIPTOR/2 authenticates the descriptor itself but does not authenticate remote peers or encrypt bearer descriptors in transit. SECURITY.md explicitly delegates this to the containing transport.

### MC-016 — external identity/attestation/policy/key/time outage behavior [HIGH]
**Related:** INV-42-C044, INV-42-C048  
No integration contract defines trust bootstrap or fail-closed behavior for unavailable external identity, attestation, policy, key, or time services.

### MC-017 — tamper-evident security audit event sink [HIGH]
**Related:** INV-42-C049, INV-42-C073, INV-42-C079  
In-memory counters exist, but security-sensitive operations are not emitted to a tamper-evident audit ledger with retention/privacy/export policy.

### MC-018 — managed key lifecycle / protected-memory integration [MEDIUM]
**Related:** INV-42-C047  
The per-table key is random and best-effort zeroized, but there is no OS/hardware protected-memory facility, rotation for long-lived sessions, or external key-management integration.

### MC-019 — fault-injection and recovery test suite [HIGH]
**Related:** INV-42-C051, INV-42-C052, INV-42-C060  
No process crash, resource pressure, forced failure, dependency failure, or recovery-objective fault tests are present.

### MC-020 — health/readiness adapter and stall thresholds [MEDIUM]
**Related:** INV-42-C052, INV-42-C071  
status() exposes bounded counters, but no readiness/health endpoint, stall threshold, dependency status, or active-capability export is implemented.

### MC-021 — metrics exporter [MEDIUM]
**Related:** INV-42-C061, INV-42-C069, INV-42-C072  
Counters are only returned in-process; no OpenTelemetry/Prometheus/other exporter, rates, latency histograms, saturation model, or resource-use metrics exist.

### MC-022 — structured logging with privacy controls [MEDIUM]
**Related:** INV-42-C073, INV-42-C075, INV-42-C079  
No structured event/log API exists. SECURITY.md says bearer descriptors must not be logged, but there is no logger adapter or redaction test.

### MC-023 — distributed tracing propagation [MEDIUM]
**Related:** INV-42-C074  
No trace-context integration exists for boundary operations.

### MC-024 — operator explain view and release/infrastructure correlation [MEDIUM]
**Related:** INV-42-C076, INV-42-C077, INV-42-C078  
Typed failures explain local rejections, but there is no operator-facing decision view, release lineage, or live infrastructure graph correlation.

### MC-025 — telemetry retention/sampling/privacy/export policy [MEDIUM]
**Related:** INV-42-C079  
No telemetry governance policy is included.

### MC-026 — dashboards and alerts [MEDIUM]
**Related:** INV-42-C080  
No dashboards, alert rules, attack/degradation classifications, or operational visualization artifacts are present.

### MC-027 — parser/input fuzzing harness [HIGH]
**Related:** INV-42-C085  
Strict parser regression tests exist, but there is no coverage-guided or property-based fuzzing corpus/harness.

### MC-028 — mixed-operation concurrency/race suite [MEDIUM]
**Related:** INV-42-C086  
Concurrent allocation uniqueness is tested; concurrent resolve/close/destroy/status races and high-contention stress are not.

### MC-029 — expanded threat-derived adversarial suite [HIGH]
**Related:** INV-42-C050, INV-42-C087  
Forgery, tamper, replay, fork, capacity, and type-confusion cases are covered, but injection/log-safety, timing/side-channel analysis, key compromise simulation, hostile Mapping/object behavior, and sustained exhaustion tests are absent.

### MC-030 — benchmark, soak, burst, overload, and fleet-scale suite [HIGH]
**Related:** INV-42-C061, INV-42-C063, INV-42-C064, INV-42-C088  
No reproducible performance harness or baseline evidence exists.

### MC-031 — cross-runtime/OS/CPU/provider compatibility matrix and CI [HIGH]
**Related:** INV-42-C084, INV-42-C093  
Only Python 3.13.5 was exercised in this audit. No supported Python/OS/CPU/hypervisor/provider matrix is tested.

### MC-032 — coverage measurement and threshold gate [MEDIUM]
**Related:** INV-42-C081, INV-42-C082, INV-42-C090  
No coverage tool/report/threshold demonstrates exercised branch coverage of runtime and certification adapter.

### MC-033 — performance thresholds and regression gate [HIGH]
**Related:** INV-42-C062, INV-42-C070  
No p50/p95/p99/worst-case acceptance thresholds or release-blocking regression rule exists.

### MC-034 — edge power/thermal measurement [MEDIUM]
**Related:** INV-42-C068  
No constrained-edge power or thermal measurement exists; applicability has not been formally marked N/A.

### MC-035 — measured SLO/error-budget and support commitment machinery [HIGH]
**Related:** INV-42-C091  
Contract SLO text is not connected to measured telemetry, burn-rate alerts, support hours, or escalation commitments.

### MC-036 — canary/staged rollout/rollback/emergency-disable automation [HIGH]
**Related:** INV-42-C092  
README/OPERATIONS describe intent, but there are no executable rollout, rollback, or emergency-disable procedures in this archive.

### MC-037 — vulnerability response, patching, EOL, and adjacent-version support policy [HIGH]
**Related:** INV-42-C093, INV-42-C094  
Protocol compatibility is documented, but dependency support windows, vulnerability SLAs, patch cadence, and EOL policy are absent.

### MC-038 — incident response runbook [HIGH]
**Related:** INV-42-C097  
No severity model, paging path, containment playbook, forensic preservation, or recovery workflow is present.

### MC-039 — recurring review automation/evidence [MEDIUM]
**Related:** INV-42-C098  
No scheduled access, dependency, architecture, configuration, or policy review workflow/evidence exists.

### MC-040 — exception/waiver/technical-debt registry [MEDIUM]
**Related:** INV-42-C099  
No owner/expiry-based waiver or technical-debt ledger is present.

### MC-041 — machine-readable acceptance evidence and formal production exit result [BLOCKER]
**Related:** INV-42-C090, INV-42-C100  
CHECKLIST.json defines requirements but no produced evidence ledger/gate result is bundled. Without pk_core and the missing integration/security/performance evidence, production exit cannot be demonstrated.

### MC-042 — policy-controlled descriptor transfer/delegation between tables [OPTIONAL]
**Related:** optional contract capability  
The contract lists descriptor transfer between tables as optional; no delegation/transfer API is implemented. This is not a mandatory v4.2.0 correctness blocker.

## Full 100-requirement audit matrix

| Check | Status | Requirement | Evidence / gap |
|---|---|---|---|
| INV-42-C001 | met | Define the exact production responsibility of Capability descriptors. | contract.py responsibility |
| INV-42-C002 | met | Document what Capability descriptors owns and explicitly does not own. | contract.py owns/not_owns |
| INV-42-C003 | met | Identify upstream, downstream, and peer dependencies of Capability descriptors. | contract.py dependencies |
| INV-42-C004 | met | Define the authoritative source of truth used by Capability descriptors. | contract.py source_of_truth |
| INV-42-C005 | partial | Document assumptions Capability descriptors makes about nodes, runtimes, networks, storage, and control planes. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C006 | met | Define tenant, environment, site, and workload boundaries relevant to Capability descriptors. | contract.py boundaries |
| INV-42-C007 | met | Separate mandatory Capability descriptors capabilities from optional optimizations. | mandatory/optional lists |
| INV-42-C008 | met | Document unsupported deployment patterns and non-goals for Capability descriptors. | non_goals |
| INV-42-C009 | missing | Assign an accountable owner and escalation path for Capability descriptors. | MC-003 |
| INV-42-C010 | met | Approve an architecture decision record for Capability descriptors, its technologies (Scoped file descriptors, network sockets, WIT imports), and its function (Explicit resource grants). | docs/ADR-0001-authenticated-descriptors.md |
| INV-42-C011 | partial | Translate the source function of Capability descriptors — Explicit resource grants — into testable SHALL-level requirements. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C012 | missing | Define functional requirements for Capability descriptors across cloud, datacenter, near-edge, and far-edge contexts where applicable. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C013 | partial | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C014 | missing | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C015 | partial | Define lifecycle states and legal state transitions managed or exposed by Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C016 | met | Define versioning and backward-compatibility requirements for Capability descriptors. | COMPATIBILITY.md and explicit v1 rejection |
| INV-42-C017 | met | Define capacity ceilings, quotas, and fairness semantics relevant to Capability descriptors. | TABLE_LIMIT and SESSION_ALLOCATION_LIMIT |
| INV-42-C018 | not-applicable-or-needs-formal-waiver | Define behavior when network connectivity is intermittent or absent. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C019 | missing | Define precedence rules when Capability descriptors requirements conflict with security, residency, SLO, or cost constraints. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C020 | missing | Maintain a requirements traceability matrix from each Capability descriptors requirement to implementation and verification evidence. | MC-004 |
| INV-42-C021 | met | Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Capability descriptors. | contract.py interfaces enumerates runtime surface |
| INV-42-C022 | met | Use versioned typed schemas for all externally visible Capability descriptors contracts. | schemas/*.schema.json + strict parser |
| INV-42-C023 | partial | Define authentication requirements at each Capability descriptors boundary. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C024 | met | Define authorization and explicit capability requirements at each Capability descriptors boundary. | per-table HMAC bearer authority |
| INV-42-C025 | missing | Define timeout, cancellation, retry, idempotency, and backpressure semantics for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C026 | met | Define structured failure codes and machine-readable error details for Capability descriptors. | DescriptorError stable codes |
| INV-42-C027 | met | Define compatibility behavior when peers use different supported versions. | COMPATIBILITY.md |
| INV-42-C028 | met | Document payload, concurrency, queue, connection, or resource limits at Capability descriptors interfaces. | coded live/session limits |
| INV-42-C029 | partial | Provide reference examples and conformance fixtures for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C030 | missing | Create automated integration tests proving Capability descriptors interoperates with adjacent architectural layers. | MC-005 |
| INV-42-C031 | missing | Select and pin approved implementations, versions, or specifications for Capability descriptors: Scoped file descriptors, network sockets, WIT imports. | MC-006/MC-007 |
| INV-42-C032 | met | Separate immutable artifacts from mutable configuration and state for Capability descriptors. | immutable code vs process-local state |
| INV-42-C033 | met | Define declarative configuration and secure defaults for Capability descriptors. | auth/limits/fork guard enabled by default |
| INV-42-C034 | met | Validate configuration before activation and fail closed on security-critical errors. | strict validation fails closed |
| INV-42-C035 | not-applicable-or-needs-formal-waiver | Support site- and environment-specific configuration without rebuilding immutable artifacts. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C036 | not-applicable-or-needs-formal-waiver | Record configuration provenance, version, author, and activation time. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C037 | not-applicable-or-needs-formal-waiver | Apply atomic or transactional configuration updates where partial application is unsafe. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C038 | not-applicable-or-needs-formal-waiver | Define automatic and operator-driven rollback for failed Capability descriptors changes. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C039 | met | Keep credentials and secret material out of ordinary Capability descriptors configuration and diagnostics. | table key is generated internally and omitted from diagnostics |
| INV-42-C040 | partial | Provide a deterministic bootstrap path from an empty node/environment to healthy Capability descriptors operation. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C041 | met | Threat-model Capability descriptors against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. | SECURITY.md threat model |
| INV-42-C042 | met | Apply least privilege to every identity and capability used by Capability descriptors. | explicit authenticated capability required for resolve |
| INV-42-C043 | met | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Capability descriptors permits. | runtime has no ambient filesystem/network/device authority |
| INV-42-C044 | partial | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C045 | missing | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Capability descriptors. | MC-014 |
| INV-42-C046 | met | Enforce tenant/workload isolation across Capability descriptors execution, memory, state, network, and device boundaries as applicable. | foreign-table descriptors fail closed |
| INV-42-C047 | partial | Encrypt sensitive Capability descriptors data in transit and at rest with managed key rotation. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C048 | missing | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C049 | missing | Emit tamper-evident audit events for security-sensitive Capability descriptors operations. | MC-017 |
| INV-42-C050 | partial | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C051 | partial | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C052 | partial | Define automated health and stall detection thresholds for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C053 | not-applicable-or-needs-formal-waiver | Implement bounded retry with backoff and jitter only where operations are safe to retry. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C054 | met | Implement admission control, load shedding, or circuit breaking to prevent Capability descriptors failure cascades. | bounded admission through table/session limits |
| INV-42-C055 | not-applicable-or-needs-formal-waiver | Define failover behavior without violating isolation, residency, or consistency requirements. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C056 | not-applicable-or-needs-formal-waiver | Provide degraded operation when noncritical dependencies are unavailable. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C057 | met | Define crash-consistency, restart, resume, or replay semantics for mutable Capability descriptors state. | OPERATIONS.md restart creates a new authority session |
| INV-42-C058 | partial | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C059 | met | Provide quarantine, freeze, disable, or isolation controls for unsafe Capability descriptors behavior. | destroy() revokes table |
| INV-42-C060 | missing | Run fault-injection tests proving Capability descriptors recovery against documented objectives. | MC-019 |
| INV-42-C061 | missing | Establish reproducible baselines for Capability descriptors latency, throughput, startup, CPU, memory, storage, network, and power overhead. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C062 | missing | Define p50, p95, p99, and worst-case performance thresholds for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C063 | missing | Measure Capability descriptors under steady load, burst load, overload, scale-out, scale-in, and recovery. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C064 | missing | Measure per-workload and per-tenant overhead introduced by Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C065 | partial | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C066 | not-applicable-or-needs-formal-waiver | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C067 | met | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. | bounded table/session allocation + RLock |
| INV-42-C068 | missing | Measure power and thermal impact on constrained edge nodes where relevant. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C069 | partial | Define capacity models and saturation signals that predict when Capability descriptors needs more resources. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C070 | missing | Block releases that regress approved Capability descriptors startup, density, throughput, or tail-latency thresholds. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C071 | partial | Expose Capability descriptors health, readiness, version, configuration, dependency status, and active capability set. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C072 | partial | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C073 | missing | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. | MC-022 |
| INV-42-C074 | missing | Propagate trace context across all relevant Capability descriptors boundaries. | MC-023 |
| INV-42-C075 | partial | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C076 | partial | Record the reason for every automated decision made by Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C077 | missing | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. | MC-024 |
| INV-42-C078 | missing | Correlate Capability descriptors events with application release lineage and the live infrastructure graph. | MC-024 |
| INV-42-C079 | missing | Define telemetry retention, sampling, privacy, and export policy. | MC-025 |
| INV-42-C080 | missing | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. | MC-026 |
| INV-42-C081 | met | Create unit tests for deterministic Capability descriptors logic and state transitions. | tests/test_descriptors.py standalone deterministic tests |
| INV-42-C082 | met | Create contract tests for every public Capability descriptors interface. | public runtime methods have regression coverage |
| INV-42-C083 | missing | Create integration tests with every supported adjacent layer and execution tier. | MC-005 |
| INV-42-C084 | missing | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Capability descriptors. | MC-031 |
| INV-42-C085 | missing | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Capability descriptors. | MC-027 |
| INV-42-C086 | partial | Create concurrency and race-condition tests for shared/distributed Capability descriptors state. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C087 | partial | Create security tests derived directly from the Capability descriptors threat model. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C088 | missing | Create benchmark, soak, burst, and fleet-scale tests appropriate to Capability descriptors. | MC-030 |
| INV-42-C089 | missing | Create disaster, partition, reconnect, and degraded-control-plane tests. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C090 | missing | Require machine-readable acceptance evidence before certifying a Capability descriptors release for production. | MC-001/MC-041 |
| INV-42-C091 | partial | Define production SLOs, error budgets, and support commitments for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C092 | partial | Define canary, staged rollout, rollback, and emergency-disable procedures for Capability descriptors. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C093 | partial | Maintain a supported-version compatibility matrix for Capability descriptors and adjacent dependencies. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C094 | missing | Define patching, vulnerability response, and end-of-life SLAs for Capability descriptors. | MC-037 |
| INV-42-C095 | met | Provide backup, restore, migration, or reconstruction procedures for Capability descriptors state where applicable. | state is intentionally ephemeral; restart reconstructs a new table session |
| INV-42-C096 | partial | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. | See missing-component inventory or repository evidence; full production evidence is not bundled. |
| INV-42-C097 | missing | Define incident severity, paging, escalation, containment, and recovery procedures. | MC-003/MC-038 |
| INV-42-C098 | missing | Perform recurring access, policy, dependency, configuration, and architecture reviews. | MC-039 |
| INV-42-C099 | missing | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. | MC-040 |
| INV-42-C100 | missing | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. | MC-001/MC-041 |

## Release conclusion

Version 4.2.0 materially improves the runtime and closes the demonstrated descriptor-forgery defect. The standalone code is testable and fail-closed for its implemented local authority model. However, this archive does not contain enough integration, supply-chain, observability, performance, operational, or machine-readable gate evidence to claim production completion of all 100 requirements. `MISSING_COMPONENTS.json` is the machine-readable inventory for the remaining work.
