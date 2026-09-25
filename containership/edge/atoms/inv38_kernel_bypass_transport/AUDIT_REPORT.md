# INV-38 post-hardening audit report

**Repository version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** the standalone archive only; external `pk_core`, sibling repositories, hardware, CI systems, and deployment infrastructure were not available for verification.

## Executive result

- **Present:** 10 / 100 checklist requirements have direct, inspectable support in this archive.
- **Partial:** 40 / 100 have some declaration, model behaviour, or test evidence but are incomplete for production certification.
- **Missing:** 50 / 100 have no sufficient implementation/evidence artifact in this archive.
- The original 4.1.0 package compiled, but its `pk_core` conformance suite executed **zero tests** locally because all three tests were skipped.
- Version 4.2.0 adds dependency-independent safety tests and repository-integrity tests; these pass in normal and optimized (`python -O`) modes.
- The archive is a hardened **reference model**, not a production kernel-bypass/RDMA transport implementation.

## Confirmed defects fixed in 4.2.0

- Removed the false README statement that `MASTER.md` was included; the file is absent.
- Prevented memory-region deregistration while descriptors for that key remain in flight.
- Added address-width overflow checks and strict constructor/range validation.
- Added registered-region and completion-backlog ceilings in addition to the existing submission-ring bound.
- Made fallback capacity failure lossless and preserved completion ordering.
- Snapshotted mutable payloads before asynchronous completion to prevent post-validation mutation/TOCTOU behaviour.
- Added lock-protected queue mutation and observable depth/count properties.
- Added stable exception error codes and dependency-independent tests.

## Missing production components / release blockers

The following component classes remain absent or materially incomplete after the hardening pass:

1. **Executable core/conformance dependency** — compatible, pinned `pk_core` plus reproducible installation/bundle metadata.
2. **Actual kernel-bypass backend** — RDMA/verbs, DPDK, io_uring or equivalent adapter; NIC/driver/firmware/IOMMU integration; pinned implementation/specification.
3. **Normative interface definitions** — typed/versioned schemas or IDL for `PK_BYPASS_MR/1`, `PK_BYPASS_POST/1`, `PK_BYPASS_CQ/1`, structured errors, compatibility negotiation and fixtures.
4. **Identity and policy plane** — authentication, authorization/capability enforcement, tenant/workload binding, attestation/policy/key/time outage behaviour.
5. **Supply-chain controls** — dependency pinning, artifact signatures/digests/provenance, SBOM, vulnerability policy, reproducible release evidence.
6. **Configuration system** — declarative schema, provenance, validation/activation, atomic updates, environment/site overlays, rollback and audit history.
7. **Full resilience mechanisms** — retry policy, health/stall detection, circuit breaking/load shedding, crash/restart/replay semantics, quarantine controls, failover invariants.
8. **Production observability** — metrics exporter, structured logs, tracing, explain/decision records, health/readiness endpoint, retention/privacy/export policy, dashboards and alerts.
9. **Performance engineering evidence** — baseline benchmarks, p50/p95/worst thresholds, overload/scale/recovery/soak tests, capacity model, per-tenant overhead, power/thermal evidence, regression gate.
10. **Integration and compatibility certification** — INV-35/36/37/GAP-12 fixtures, CPU/OS/hypervisor/provider/protocol matrix, fuzzing, race/fault/disaster/security test suites.
11. **Operations/governance artifacts** — owner/escalation, ADR, support/EOL/vulnerability SLAs, canary/staged rollout, incident runbook, compatibility matrix, review cadence, waiver/debt register.
12. **Source/evidence corpus gap** — `MASTER.md` referenced by the earlier README is not present; no replacement 100-item master prompt/workflow corpus is included.

## Additional repository-level gaps found

These are not all separate checklist rows, but they are missing release/maintenance artifacts in the delivered repository:

- No `LICENSE`/`NOTICE` file identifying redistribution terms.
- No `pyproject.toml`/package metadata, dependency declaration, or reproducible dependency lock for `pk_core`.
- No CI workflow or machine-readable build/release pipeline configuration.
- No static-type/lint/security-scan configuration or pinned toolchain.
- No `SECURITY.md`, vulnerability reporting process, `CODEOWNERS`, or maintainer/ownership metadata.
- No `CONTRIBUTING.md` or development/review workflow.
- No SBOM, signed checksum/provenance attestation, or release signature.
- No benchmark datasets/results, hardware qualification records, or production deployment manifests.

## 100-requirement evidence matrix

| ID | Status | Requirement | Archive evidence / gap |
|---|---|---|---|
| INV-38-C001 | PRESENT | Define the exact production responsibility of Kernel-bypass transport. | `contract.py` defines the production responsibility. |
| INV-38-C002 | PRESENT | Document what Kernel-bypass transport owns and explicitly does not own. | `contract.py` lists owned and explicitly non-owned responsibilities. |
| INV-38-C003 | PRESENT | Identify upstream, downstream, and peer dependencies of Kernel-bypass transport. | `contract.py` names four upstream/downstream/peer dependencies. |
| INV-38-C004 | PRESENT | Define the authoritative source of truth used by Kernel-bypass transport. | Registration table is declared as the source of truth. |
| INV-38-C005 | PRESENT | Document assumptions Kernel-bypass transport makes about nodes, runtimes, networks, storage, and control planes. | Three cross-system assumptions are declared. |
| INV-38-C006 | PRESENT | Define tenant, environment, site, and workload boundaries relevant to Kernel-bypass transport. | Tenant/environment/site/workload boundaries are declared. |
| INV-38-C007 | PRESENT | Separate mandatory Kernel-bypass transport capabilities from optional optimizations. | Mandatory and optional capability lists are separated. |
| INV-38-C008 | PRESENT | Document unsupported deployment patterns and non-goals for Kernel-bypass transport. | Non-goals are explicitly listed. |
| INV-38-C009 | MISSING | Assign an accountable owner and escalation path for Kernel-bypass transport. | No accountable owner, on-call destination, or escalation path artifact. |
| INV-38-C010 | MISSING | Approve an architecture decision record for Kernel-bypass transport, its technologies (RDMA), and its function (Direct placement of network payloads into guest memory). | No ADR approving RDMA technology, alternatives, tradeoffs, or decision date. |
| INV-38-C011 | PARTIAL | Translate the source function of Kernel-bypass transport — Direct placement of network payloads into guest memory — into testable SHALL-level requirements. | Mandatory behaviours exist, but they are not a numbered normative SHALL specification with acceptance criteria. |
| INV-38-C012 | MISSING | Define functional requirements for Kernel-bypass transport across cloud, datacenter, near-edge, and far-edge contexts where applicable. | No context-specific requirements for cloud/datacenter/near-edge/far-edge operation. |
| INV-38-C013 | PARTIAL | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. | Three SLO statements exist, but availability/durability/isolation/determinism and full threshold definitions are incomplete. |
| INV-38-C014 | MISSING | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Kernel-bypass transport. | No explicit success/partial/degraded/retryable/terminal outcome model. |
| INV-38-C015 | MISSING | Define lifecycle states and legal state transitions managed or exposed by Kernel-bypass transport. | No lifecycle state machine or legal-transition table. |
| INV-38-C016 | PARTIAL | Define versioning and backward-compatibility requirements for Kernel-bypass transport. | Version metadata exists, but no compatibility/deprecation policy or supported-version rules. |
| INV-38-C017 | PARTIAL | Define capacity ceilings, quotas, and fairness semantics relevant to Kernel-bypass transport. | Queue/region/completion ceilings now exist; tenant/workload quotas and fairness are absent. |
| INV-38-C018 | PARTIAL | Define behavior when network connectivity is intermittent or absent. | Kernel fallback exists for bypass unavailability; disconnected/intermittent network semantics are not specified. |
| INV-38-C019 | MISSING | Define precedence rules when Kernel-bypass transport requirements conflict with security, residency, SLO, or cost constraints. | No precedence rules for security, residency, SLO, and cost conflicts. |
| INV-38-C020 | MISSING | Maintain a requirements traceability matrix from each Kernel-bypass transport requirement to implementation and verification evidence. | No requirements-to-code-to-test traceability matrix. |
| INV-38-C021 | PARTIAL | Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Kernel-bypass transport. | Three logical interfaces are named, but there is no exhaustive API/device/control-plane boundary inventory. |
| INV-38-C022 | MISSING | Use versioned typed schemas for all externally visible Kernel-bypass transport contracts. | Interface names are versioned, but no typed external schema/WIT/IDL/JSON-schema artifacts exist. |
| INV-38-C023 | MISSING | Define authentication requirements at each Kernel-bypass transport boundary. | No authentication requirements per boundary. |
| INV-38-C024 | MISSING | Define authorization and explicit capability requirements at each Kernel-bypass transport boundary. | No authorization/capability model per boundary. |
| INV-38-C025 | PARTIAL | Define timeout, cancellation, retry, idempotency, and backpressure semantics for Kernel-bypass transport. | Ring-full backpressure exists; timeout/cancellation/retry/idempotency semantics are not defined. |
| INV-38-C026 | PARTIAL | Define structured failure codes and machine-readable error details for Kernel-bypass transport. | Exceptions now carry stable error codes, but structured error payload/details schemas are absent. |
| INV-38-C027 | MISSING | Define compatibility behavior when peers use different supported versions. | No mixed-version peer compatibility negotiation/behaviour. |
| INV-38-C028 | PARTIAL | Document payload, concurrency, queue, connection, or resource limits at Kernel-bypass transport interfaces. | Reference-model queue/region/completion limits exist but interface-level limits are not fully documented or negotiated. |
| INV-38-C029 | PARTIAL | Provide reference examples and conformance fixtures for Kernel-bypass transport. | Unit examples exist only through tests; no reusable conformance fixture corpus/reference vectors. |
| INV-38-C030 | PARTIAL | Create automated integration tests proving Kernel-bypass transport interoperates with adjacent architectural layers. | Optional INV-36 sealing interop is exercised when resolvable; the other adjacent layers are not covered. |
| INV-38-C031 | MISSING | Select and pin approved implementations, versions, or specifications for Kernel-bypass transport: RDMA. | No pinned RDMA spec/provider/NIC/driver/firmware/runtime implementation. |
| INV-38-C032 | MISSING | Separate immutable artifacts from mutable configuration and state for Kernel-bypass transport. | No documented separation of immutable artifacts from mutable config/state. |
| INV-38-C033 | PARTIAL | Define declarative configuration and secure defaults for Kernel-bypass transport. | Secure bounded defaults exist in the dataclass; there is no declarative configuration format/schema. |
| INV-38-C034 | PARTIAL | Validate configuration before activation and fail closed on security-critical errors. | Constructor validation fails closed for local limits/ranges; there is no full activation/config validation pipeline. |
| INV-38-C035 | PARTIAL | Support site- and environment-specific configuration without rebuilding immutable artifacts. | Constructor parameters allow some tuning without source edits; no site/environment configuration mechanism exists. |
| INV-38-C036 | MISSING | Record configuration provenance, version, author, and activation time. | No configuration provenance, author, version, activation timestamp, or history. |
| INV-38-C037 | MISSING | Apply atomic or transactional configuration updates where partial application is unsafe. | No transactional/atomic runtime configuration update mechanism. |
| INV-38-C038 | PARTIAL | Define automatic and operator-driven rollback for failed Kernel-bypass transport changes. | README mentions evidence-head rollback/emergency removal; runtime/data-path configuration rollback is not implemented. |
| INV-38-C039 | PARTIAL | Keep credentials and secret material out of ordinary Kernel-bypass transport configuration and diagnostics. | No secrets are stored by the model, but there is no enforced secret-redaction/configuration policy. |
| INV-38-C040 | PARTIAL | Provide a deterministic bootstrap path from an empty node/environment to healthy Kernel-bypass transport operation. | Bootstrap steps are described, but the archive omits `pk_core`, so the documented production bootstrap is not self-contained. |
| INV-38-C041 | PARTIAL | Threat-model Kernel-bypass transport against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. | Four specific threats are listed; the required full malicious-tenant/workload/supply-chain/control-plane threat model is incomplete. |
| INV-38-C042 | MISSING | Apply least privilege to every identity and capability used by Kernel-bypass transport. | No least-privilege identity/device capability design or enforcement. |
| INV-38-C043 | MISSING | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Kernel-bypass transport permits. | No explicit ambient filesystem/network/device/kernel/secret authority elimination model. |
| INV-38-C044 | MISSING | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. | No authentication of nodes, peers, artifacts, providers, or control-plane actors. |
| INV-38-C045 | MISSING | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Kernel-bypass transport. | No signature/digest/provenance verification for executable or policy artifacts. |
| INV-38-C046 | PARTIAL | Enforce tenant/workload isolation across Kernel-bypass transport execution, memory, state, network, and device boundaries as applicable. | Isolation boundaries are declared, but the reference model has no tenant/workload identity on regions/queues and no enforcement test. |
| INV-38-C047 | PARTIAL | Encrypt sensitive Kernel-bypass transport data in transit and at rest with managed key rotation. | INV-36 sealed-frame preservation is conditionally tested; at-rest encryption and managed key rotation are absent. |
| INV-38-C048 | MISSING | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. | No safe-mode semantics for unavailable identity/attestation/policy/key/time services. |
| INV-38-C049 | MISSING | Emit tamper-evident audit events for security-sensitive Kernel-bypass transport operations. | No local tamper-evident security audit event stream. Any `pk_core` evidence facility is external and unavailable here. |
| INV-38-C050 | PARTIAL | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. | Bounds/stale-key/resource tests cover some hostile inputs; privilege escalation, injection, replay, spoofing, escape, side-channel, and broader exhaustion tests are absent. |
| INV-38-C051 | PARTIAL | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Kernel-bypass transport. | Four failure modes are declared; process/VM/node/site/provider/dependency/control-plane failure enumeration is incomplete. |
| INV-38-C052 | MISSING | Define automated health and stall detection thresholds for Kernel-bypass transport. | No automated health/stall thresholds. |
| INV-38-C053 | MISSING | Implement bounded retry with backoff and jitter only where operations are safe to retry. | No bounded retry/backoff/jitter implementation or retry-safety classification. |
| INV-38-C054 | PARTIAL | Implement admission control, load shedding, or circuit breaking to prevent Kernel-bypass transport failure cascades. | Bounded rings/regions/completions provide basic admission pressure; no load shedding/circuit breaker policy. |
| INV-38-C055 | PARTIAL | Define failover behavior without violating isolation, residency, or consistency requirements. | Kernel fallback is implemented; failover rules for isolation/residency/consistency are not defined. |
| INV-38-C056 | PRESENT | Provide degraded operation when noncritical dependencies are unavailable. | `available=False` transparently routes valid posts through the kernel fallback while preserving completion order. |
| INV-38-C057 | MISSING | Define crash-consistency, restart, resume, or replay semantics for mutable Kernel-bypass transport state. | No crash-consistency, restart, resume, or replay semantics for mutable state. |
| INV-38-C058 | MISSING | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. | No split-brain/duplicate-ownership/stale-controller analysis or explicit not-applicable rationale. |
| INV-38-C059 | PARTIAL | Provide quarantine, freeze, disable, or isolation controls for unsafe Kernel-bypass transport behavior. | Bypass can be disabled via `available`; no authenticated operator quarantine/freeze control or audit trail. |
| INV-38-C060 | PARTIAL | Run fault-injection tests proving Kernel-bypass transport recovery against documented objectives. | Standalone tests inject bounds/ring/fallback failures; no systematic fault-injection harness tied to recovery objectives. |
| INV-38-C061 | MISSING | Establish reproducible baselines for Kernel-bypass transport latency, throughput, startup, CPU, memory, storage, network, and power overhead. | No reproducible latency/throughput/startup/CPU/memory/storage/network/power baseline artifacts. |
| INV-38-C062 | PARTIAL | Define p50, p95, p99, and worst-case performance thresholds for Kernel-bypass transport. | A p99 latency target exists; p50/p95/worst-case thresholds are missing and no measurement validates the target. |
| INV-38-C063 | MISSING | Measure Kernel-bypass transport under steady load, burst load, overload, scale-out, scale-in, and recovery. | No steady/burst/overload/scale-out/scale-in/recovery performance campaign. |
| INV-38-C064 | MISSING | Measure per-workload and per-tenant overhead introduced by Kernel-bypass transport. | No per-tenant/per-workload overhead measurement. |
| INV-38-C065 | PARTIAL | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Kernel-bypass transport. | The design removes a kernel path and the model intentionally snapshots mutable payloads, but no copy/context-switch/hop analysis or profile exists. |
| INV-38-C066 | PARTIAL | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. | The model represents kernel bypass and permits batching conceptually; no production zero-copy/direct-composition implementation is present. |
| INV-38-C067 | PARTIAL | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. | Ring, region count, completion backlog and address ranges are bounded; total buffered bytes, concurrency/fan-out and per-tenant bounds remain unspecified. |
| INV-38-C068 | MISSING | Measure power and thermal impact on constrained edge nodes where relevant. | No power or thermal measurement for edge nodes. |
| INV-38-C069 | PARTIAL | Define capacity models and saturation signals that predict when Kernel-bypass transport needs more resources. | Depth/count gauges exist in the model, but no capacity model or scaling threshold predicts saturation. |
| INV-38-C070 | MISSING | Block releases that regress approved Kernel-bypass transport startup, density, throughput, or tail-latency thresholds. | No release gate that compares performance baselines and blocks regressions. |
| INV-38-C071 | MISSING | Expose Kernel-bypass transport health, readiness, version, configuration, dependency status, and active capability set. | No health/readiness/version/config/dependency/capability status endpoint or snapshot. |
| INV-38-C072 | PARTIAL | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. | Some counters/depth properties exist; no structured metrics exporter for rate/error/latency/saturation/resource use. |
| INV-38-C073 | MISSING | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. | No structured logging with node/tenant/workload/component/operation identifiers. |
| INV-38-C074 | MISSING | Propagate trace context across all relevant Kernel-bypass transport boundaries. | No trace-context propagation. |
| INV-38-C075 | MISSING | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. | No safe high-cardinality diagnostic facility or redaction controls. |
| INV-38-C076 | MISSING | Record the reason for every automated decision made by Kernel-bypass transport. | No durable reason record for automated decisions/fallbacks/rejections. |
| INV-38-C077 | MISSING | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. | No operator-readable explain view. |
| INV-38-C078 | MISSING | Correlate Kernel-bypass transport events with application release lineage and the live infrastructure graph. | No correlation with application release lineage or live infrastructure graph. |
| INV-38-C079 | MISSING | Define telemetry retention, sampling, privacy, and export policy. | No telemetry retention/sampling/privacy/export policy. |
| INV-38-C080 | MISSING | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. | No dashboards or alert definitions. |
| INV-38-C081 | PRESENT | Create unit tests for deterministic Kernel-bypass transport logic and state transitions. | `tests/test_transport.py` now provides deterministic local unit tests independent of `pk_core`. |
| INV-38-C082 | PARTIAL | Create contract tests for every public Kernel-bypass transport interface. | Public reference-model methods are tested, but there are no typed-contract tests for every externally visible `PK_BYPASS_*` interface. |
| INV-38-C083 | PARTIAL | Create integration tests with every supported adjacent layer and execution tier. | Only conditional INV-36 integration is present; INV-35/INV-37/GAP-12 and tier-specific integrations are absent. |
| INV-38-C084 | MISSING | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Kernel-bypass transport. | No CPU/OS/runtime/hypervisor/provider/protocol compatibility test matrix. |
| INV-38-C085 | MISSING | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Kernel-bypass transport. | No fuzz/property-based testing of untrusted inputs or schemas. |
| INV-38-C086 | PARTIAL | Create concurrency and race-condition tests for shared/distributed Kernel-bypass transport state. | A concurrent posting test exists; lifecycle races (post/poll/deregister/fallback/config changes) are not comprehensively stressed. |
| INV-38-C087 | PARTIAL | Create security tests derived directly from the Kernel-bypass transport threat model. | Some threat-derived tests cover OOB, stale keys, overflow and mutable-input TOCTOU; the threat-model security suite is incomplete. |
| INV-38-C088 | MISSING | Create benchmark, soak, burst, and fleet-scale tests appropriate to Kernel-bypass transport. | No benchmark, soak, burst, or fleet-scale test suite. |
| INV-38-C089 | MISSING | Create disaster, partition, reconnect, and degraded-control-plane tests. | No disaster/partition/reconnect/degraded-control-plane tests. |
| INV-38-C090 | MISSING | Require machine-readable acceptance evidence before certifying a Kernel-bypass transport release for production. | No machine-readable release acceptance evidence produced inside this archive; the documented evidence path depends on absent `pk_core`. |
| INV-38-C091 | PARTIAL | Define production SLOs, error budgets, and support commitments for Kernel-bypass transport. | Three SLO/error-budget statements exist; support commitments and operational ownership are missing. |
| INV-38-C092 | PARTIAL | Define canary, staged rollout, rollback, and emergency-disable procedures for Kernel-bypass transport. | Rollback/emergency-disable guidance exists at a high level; no canary/staged rollout procedure or tested rollback automation. |
| INV-38-C093 | MISSING | Maintain a supported-version compatibility matrix for Kernel-bypass transport and adjacent dependencies. | No supported-version compatibility matrix for this component and adjacent dependencies. |
| INV-38-C094 | MISSING | Define patching, vulnerability response, and end-of-life SLAs for Kernel-bypass transport. | No patching cadence, vulnerability response SLA, or end-of-life policy. |
| INV-38-C095 | MISSING | Provide backup, restore, migration, or reconstruction procedures for Kernel-bypass transport state where applicable. | No backup/restore/migration/reconstruction procedure or explicit proof that all mutable state is reconstructible/ephemeral. |
| INV-38-C096 | PARTIAL | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. | Day-0/day-1/day-2 bullets exist, but they are not full executable runbooks with prerequisites, validation, rollback and troubleshooting. |
| INV-38-C097 | MISSING | Define incident severity, paging, escalation, containment, and recovery procedures. | No incident severity, paging, escalation, containment, or recovery runbook. |
| INV-38-C098 | MISSING | Perform recurring access, policy, dependency, configuration, and architecture reviews. | No recurring access/policy/dependency/configuration/architecture review procedure. |
| INV-38-C099 | MISSING | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. | No exception/waiver/technical-debt/deprecation register with owner and expiry. |
| INV-38-C100 | PARTIAL | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. | A `pk_core gate` command is documented, but the core/evidence artifacts are absent and the local archive cannot independently execute a formal production exit gate. |

## Verification performed on the updated tree

- ZIP traversal check: no absolute or parent-traversal members in the source archive.
- Python syntax compilation: `python -m compileall` passes.
- Standalone transport safety suite: 9/9 tests pass in normal mode and under `python -O`.
- Repository-integrity suite: 5/5 checks pass, covering checklist cardinality, synchronized versions, degraded package import, missing-document claims, and production-source bare asserts.
- Aggregate `pytest` run: 14 passed, 3 skipped; the skips are the `pk_core`-dependent conformance tests.
- `pk_core` conformance suite: remains skipped because `pk_core` is not present in the archive/environment; this is explicitly **not** counted as production conformance evidence.

## Audit interpretation

A `PRESENT` mark means this archive contains direct evidence for the narrow checklist requirement; it does **not** mean a hardware-backed production deployment has been certified. `PARTIAL` means some relevant declaration/logic/test exists but required production scope is missing. `MISSING` means no sufficient artifact or behaviour was found in the standalone repository.
