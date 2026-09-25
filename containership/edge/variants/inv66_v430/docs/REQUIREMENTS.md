# INV-66 normative requirements (generated)

Document ID `INV66-REQ` · version 4.3.0 · generated 2026-09-23T00:00:00Z from CHECKLIST.json + RTM · owner: service owner · a change to any SHALL requires an impact note in CHANGELOG.md and regeneration.

Keywords SHALL / SHALL NOT per RFC 2119/8174. Acceptance evidence for each requirement is the RTM row (`governance/RTM.json`), which names the component closures, tests and waivers.

## Security invariants (non-overridable)

- **REQ-INV66-S01** The control plane SHALL NOT deliver any manifest to INV-63 unless a durable `admission` entry with `admitted: true` exists and no freeze covers its scope. *Evidence:* test_service, test_durability (disk full, crash), test_ha (fencing).
- **REQ-INV66-S02** Every request SHALL be authenticated by a trusted issuer token; caller-supplied identity fields SHALL be ignored. *Evidence:* test_security.AuthnTest.
- **REQ-INV66-S03** Admission SHALL require a digest-pinned image from an approved registry with a valid Ed25519 signature by an approved, unexpired signer and all required attestations. *Evidence:* test_service, test_security.
- **REQ-INV66-S04** Unavailability of the store or policy engine SHALL fail closed. *Evidence:* test_service, test_durability.
- **REQ-INV66-S05** Every admission, refusal and administrative change SHALL be journalled with a hash chain verifiable end to end and anchored externally. *Evidence:* test_durability.
- **REQ-INV66-S06** Cross-tenant reads and writes SHALL be denied unless a binding grants the capability on that scope; explicit deny SHALL win. *Evidence:* test_security.

## Performance

- **REQ-INV66-P01** Admission latency SHALL be p99 < 50 ms at offered load ≤ 70 % of measured single-writer throughput. *Evidence:* perf/results.json gate.

## Checklist-derived requirements

| Req ID | SHALL statement | Status | Basis |
|---|---|---|---|
| REQ-INV66-C001 | INV-66 SHALL satisfy: Define the exact production responsibility of Enterprise Wasm control plane. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C002 | INV-66 SHALL satisfy: Document what Enterprise Wasm control plane owns and explicitly does not own. | PASS_LOCAL | via MC-069 |
| REQ-INV66-C003 | INV-66 SHALL satisfy: Identify upstream, downstream, and peer dependencies of Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-004, MC-019, MC-020 |
| REQ-INV66-C004 | INV-66 SHALL satisfy: Define the authoritative source of truth used by Enterprise Wasm control plane. | PASS_LOCAL | via MC-005 |
| REQ-INV66-C005 | INV-66 SHALL satisfy: Document assumptions Enterprise Wasm control plane makes about nodes, runtimes, networks, storage, and control planes. | PASS_LOCAL | via MC-004 |
| REQ-INV66-C006 | INV-66 SHALL satisfy: Define tenant, environment, site, and workload boundaries relevant to Enterprise Wasm control plane. | PASS_LOCAL | via MC-004, MC-032 |
| REQ-INV66-C007 | INV-66 SHALL satisfy: Separate mandatory Enterprise Wasm control plane capabilities from optional optimizations. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C008 | INV-66 SHALL satisfy: Document unsupported deployment patterns and non-goals for Enterprise Wasm control plane. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C009 | INV-66 SHALL satisfy: Assign an accountable owner and escalation path for Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-003 |
| REQ-INV66-C010 | INV-66 SHALL satisfy: Approve an architecture decision record for Enterprise Wasm control plane, its technologies (Cosmonic Control), and its function (Enterprise management/GitOps for wasmCloud). | WAIVED_PARTIAL | via MC-002 |
| REQ-INV66-C011 | INV-66 SHALL satisfy: Translate the source function of Enterprise Wasm control plane — Enterprise management/GitOps for wasmCloud — into testable SHALL-level requirements. | PASS_LOCAL | via MC-006, MC-021, MC-069 |
| REQ-INV66-C012 | INV-66 SHALL satisfy: Define functional requirements for Enterprise Wasm control plane across cloud, datacenter, near-edge, and far-edge contexts where applicable. | PASS_LOCAL | via MC-006, MC-021 |
| REQ-INV66-C013 | INV-66 SHALL satisfy: Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. | PASS_LOCAL | via MC-006 |
| REQ-INV66-C014 | INV-66 SHALL satisfy: Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Enterprise Wasm control plane. | PASS_LOCAL | via MC-006, MC-008 |
| REQ-INV66-C015 | INV-66 SHALL satisfy: Define lifecycle states and legal state transitions managed or exposed by Enterprise Wasm control plane. | PASS_LOCAL | via MC-006, MC-008 |
| REQ-INV66-C016 | INV-66 SHALL satisfy: Define versioning and backward-compatibility requirements for Enterprise Wasm control plane. | PASS_LOCAL | via MC-006, MC-018 |
| REQ-INV66-C017 | INV-66 SHALL satisfy: Define capacity ceilings, quotas, and fairness semantics relevant to Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-006, MC-009 |
| REQ-INV66-C018 | INV-66 SHALL satisfy: Define behavior when network connectivity is intermittent or absent. | PASS_LOCAL | via MC-006, MC-010 |
| REQ-INV66-C019 | INV-66 SHALL satisfy: Define precedence rules when Enterprise Wasm control plane requirements conflict with security, residency, SLO, or cost constraints. | WAIVED_PARTIAL | via MC-006, MC-011, MC-033 |
| REQ-INV66-C020 | INV-66 SHALL satisfy: Maintain a requirements traceability matrix from each Enterprise Wasm control plane requirement to implementation and verification evidence. | WAIVED_PARTIAL | via MC-001, MC-007 |
| REQ-INV66-C021 | INV-66 SHALL satisfy: Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-012, MC-013, MC-014, MC-019, MC-021, MC-069 |
| REQ-INV66-C022 | INV-66 SHALL satisfy: Use versioned typed schemas for all externally visible Enterprise Wasm control plane contracts. | PASS_LOCAL | via MC-012, MC-013, MC-014 |
| REQ-INV66-C023 | INV-66 SHALL satisfy: Define authentication requirements at each Enterprise Wasm control plane boundary. | WAIVED_PARTIAL | via MC-013, MC-015, MC-031 |
| REQ-INV66-C024 | INV-66 SHALL satisfy: Define authorization and explicit capability requirements at each Enterprise Wasm control plane boundary. | PASS_LOCAL | via MC-013, MC-032 |
| REQ-INV66-C025 | INV-66 SHALL satisfy: Define timeout, cancellation, retry, idempotency, and backpressure semantics for Enterprise Wasm control plane. | PASS_LOCAL | via MC-017 |
| REQ-INV66-C026 | INV-66 SHALL satisfy: Define structured failure codes and machine-readable error details for Enterprise Wasm control plane. | PASS_LOCAL | via MC-016 |
| REQ-INV66-C027 | INV-66 SHALL satisfy: Define compatibility behavior when peers use different supported versions. | PASS_LOCAL | via MC-014, MC-018 |
| REQ-INV66-C028 | INV-66 SHALL satisfy: Document payload, concurrency, queue, connection, or resource limits at Enterprise Wasm control plane interfaces. | WAIVED_PARTIAL | via MC-009, MC-017 |
| REQ-INV66-C029 | INV-66 SHALL satisfy: Provide reference examples and conformance fixtures for Enterprise Wasm control plane. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C030 | INV-66 SHALL satisfy: Create automated integration tests proving Enterprise Wasm control plane interoperates with adjacent architectural layers. | WAIVED_PARTIAL | via MC-019, MC-020, MC-021, MC-033, MC-056 |
| REQ-INV66-C031 | INV-66 SHALL satisfy: Select and pin approved implementations, versions, or specifications for Enterprise Wasm control plane: Cosmonic Control. | WAIVED_PARTIAL | via MC-028 |
| REQ-INV66-C032 | INV-66 SHALL satisfy: Separate immutable artifacts from mutable configuration and state for Enterprise Wasm control plane. | PASS_LOCAL | via MC-005, MC-025, MC-026 |
| REQ-INV66-C033 | INV-66 SHALL satisfy: Define declarative configuration and secure defaults for Enterprise Wasm control plane. | PASS_LOCAL | via MC-022, MC-025, MC-026 |
| REQ-INV66-C034 | INV-66 SHALL satisfy: Validate configuration before activation and fail closed on security-critical errors. | PASS_LOCAL | via MC-022, MC-025, MC-026 |
| REQ-INV66-C035 | INV-66 SHALL satisfy: Support site- and environment-specific configuration without rebuilding immutable artifacts. | PASS_LOCAL | via MC-022, MC-025, MC-026 |
| REQ-INV66-C036 | INV-66 SHALL satisfy: Record configuration provenance, version, author, and activation time. | PASS_LOCAL | via MC-023, MC-025, MC-026 |
| REQ-INV66-C037 | INV-66 SHALL satisfy: Apply atomic or transactional configuration updates where partial application is unsafe. | PASS_LOCAL | via MC-024, MC-025, MC-026 |
| REQ-INV66-C038 | INV-66 SHALL satisfy: Define automatic and operator-driven rollback for failed Enterprise Wasm control plane changes. | PASS_LOCAL | via MC-024, MC-025, MC-026 |
| REQ-INV66-C039 | INV-66 SHALL satisfy: Keep credentials and secret material out of ordinary Enterprise Wasm control plane configuration and diagnostics. | PASS_LOCAL | via MC-027 |
| REQ-INV66-C040 | INV-66 SHALL satisfy: Provide a deterministic bootstrap path from an empty node/environment to healthy Enterprise Wasm control plane operation. | WAIVED_PARTIAL | via MC-028 |
| REQ-INV66-C041 | INV-66 SHALL satisfy: Threat-model Enterprise Wasm control plane against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. | PASS_LOCAL | via MC-036 |
| REQ-INV66-C042 | INV-66 SHALL satisfy: Apply least privilege to every identity and capability used by Enterprise Wasm control plane. | PASS_LOCAL | via MC-032 |
| REQ-INV66-C043 | INV-66 SHALL satisfy: Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Enterprise Wasm control plane permits. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C044 | INV-66 SHALL satisfy: Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. | WAIVED_PARTIAL | via MC-015, MC-031 |
| REQ-INV66-C045 | INV-66 SHALL satisfy: Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-026, MC-029, MC-030 |
| REQ-INV66-C046 | INV-66 SHALL satisfy: Enforce tenant/workload isolation across Enterprise Wasm control plane execution, memory, state, network, and device boundaries as applicable. | PASS_LOCAL | via MC-032 |
| REQ-INV66-C047 | INV-66 SHALL satisfy: Encrypt sensitive Enterprise Wasm control plane data in transit and at rest with managed key rotation. | WAIVED_PARTIAL | via MC-027, MC-034 |
| REQ-INV66-C048 | INV-66 SHALL satisfy: Define safe behavior when identity, attestation, policy, key, or time services are unavailable. | WAIVED_PARTIAL | via MC-010, MC-027, MC-033 |
| REQ-INV66-C049 | INV-66 SHALL satisfy: Emit tamper-evident audit events for security-sensitive Enterprise Wasm control plane operations. | WAIVED_PARTIAL | via MC-035, MC-070 |
| REQ-INV66-C050 | INV-66 SHALL satisfy: Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. | PASS_LOCAL | via MC-037 |
| REQ-INV66-C051 | INV-66 SHALL satisfy: Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-004, MC-019 |
| REQ-INV66-C052 | INV-66 SHALL satisfy: Define automated health and stall detection thresholds for Enterprise Wasm control plane. | PASS_LOCAL | via MC-040 |
| REQ-INV66-C053 | INV-66 SHALL satisfy: Implement bounded retry with backoff and jitter only where operations are safe to retry. | PASS_LOCAL | via MC-017, MC-041 |
| REQ-INV66-C054 | INV-66 SHALL satisfy: Implement admission control, load shedding, or circuit breaking to prevent Enterprise Wasm control plane failure cascades. | PASS_LOCAL | via MC-017, MC-041 |
| REQ-INV66-C055 | INV-66 SHALL satisfy: Define failover behavior without violating isolation, residency, or consistency requirements. | WAIVED_PARTIAL | via MC-010, MC-039 |
| REQ-INV66-C056 | INV-66 SHALL satisfy: Provide degraded operation when noncritical dependencies are unavailable. | PASS_LOCAL | via MC-010, MC-040 |
| REQ-INV66-C057 | INV-66 SHALL satisfy: Define crash-consistency, restart, resume, or replay semantics for mutable Enterprise Wasm control plane state. | PASS_LOCAL | via MC-005, MC-010, MC-038 |
| REQ-INV66-C058 | INV-66 SHALL satisfy: Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. | WAIVED_PARTIAL | via MC-039 |
| REQ-INV66-C059 | INV-66 SHALL satisfy: Provide quarantine, freeze, disable, or isolation controls for unsafe Enterprise Wasm control plane behavior. | PASS_LOCAL | via MC-042 |
| REQ-INV66-C060 | INV-66 SHALL satisfy: Run fault-injection tests proving Enterprise Wasm control plane recovery against documented objectives. | PASS_LOCAL | via MC-043 |
| REQ-INV66-C061 | INV-66 SHALL satisfy: Establish reproducible baselines for Enterprise Wasm control plane latency, throughput, startup, CPU, memory, storage, network, and power overhead. | PASS_LOCAL | via MC-044 |
| REQ-INV66-C062 | INV-66 SHALL satisfy: Define p50, p95, p99, and worst-case performance thresholds for Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-044, MC-045 |
| REQ-INV66-C063 | INV-66 SHALL satisfy: Measure Enterprise Wasm control plane under steady load, burst load, overload, scale-out, scale-in, and recovery. | PASS_LOCAL | via MC-044 |
| REQ-INV66-C064 | INV-66 SHALL satisfy: Measure per-workload and per-tenant overhead introduced by Enterprise Wasm control plane. | PASS_LOCAL | via MC-044 |
| REQ-INV66-C065 | INV-66 SHALL satisfy: Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Enterprise Wasm control plane. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C066 | INV-66 SHALL satisfy: Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C067 | INV-66 SHALL satisfy: Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. | WAIVED_PARTIAL | via MC-009, MC-046 |
| REQ-INV66-C068 | INV-66 SHALL satisfy: Measure power and thermal impact on constrained edge nodes where relevant. | NOT_APPLICABLE | via MC-048 |
| REQ-INV66-C069 | INV-66 SHALL satisfy: Define capacity models and saturation signals that predict when Enterprise Wasm control plane needs more resources. | WAIVED_PARTIAL | via MC-009, MC-047 |
| REQ-INV66-C070 | INV-66 SHALL satisfy: Block releases that regress approved Enterprise Wasm control plane startup, density, throughput, or tail-latency thresholds. | WAIVED_PARTIAL | via MC-045 |
| REQ-INV66-C071 | INV-66 SHALL satisfy: Expose Enterprise Wasm control plane health, readiness, version, configuration, dependency status, and active capability set. | PASS_LOCAL | via MC-049 |
| REQ-INV66-C072 | INV-66 SHALL satisfy: Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. | PASS_LOCAL | via MC-050 |
| REQ-INV66-C073 | INV-66 SHALL satisfy: Emit structured logs with stable node, tenant, workload, component, and operation identifiers. | PASS_LOCAL | via MC-051 |
| REQ-INV66-C074 | INV-66 SHALL satisfy: Propagate trace context across all relevant Enterprise Wasm control plane boundaries. | PASS_LOCAL | via MC-052 |
| REQ-INV66-C075 | INV-66 SHALL satisfy: Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. | PASS_LOCAL | via MC-051 |
| REQ-INV66-C076 | INV-66 SHALL satisfy: Record the reason for every automated decision made by Enterprise Wasm control plane. | PASS_LOCAL | via MC-053 |
| REQ-INV66-C077 | INV-66 SHALL satisfy: Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. | PASS_LOCAL | via MC-053 |
| REQ-INV66-C078 | INV-66 SHALL satisfy: Correlate Enterprise Wasm control plane events with application release lineage and the live infrastructure graph. | PASS_LOCAL | via MC-053 |
| REQ-INV66-C079 | INV-66 SHALL satisfy: Define telemetry retention, sampling, privacy, and export policy. | WAIVED_PARTIAL | via MC-054, MC-070 |
| REQ-INV66-C080 | INV-66 SHALL satisfy: Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. | PASS_LOCAL | via MC-054 |
| REQ-INV66-C081 | INV-66 SHALL satisfy: Create unit tests for deterministic Enterprise Wasm control plane logic and state transitions. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C082 | INV-66 SHALL satisfy: Create contract tests for every public Enterprise Wasm control plane interface. | PASS_LOCAL | via MC-012, MC-055 |
| REQ-INV66-C083 | INV-66 SHALL satisfy: Create integration tests with every supported adjacent layer and execution tier. | WAIVED_PARTIAL | via MC-020, MC-056 |
| REQ-INV66-C084 | INV-66 SHALL satisfy: Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-057 |
| REQ-INV66-C085 | INV-66 SHALL satisfy: Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Enterprise Wasm control plane. | PASS_LOCAL | via MC-037 |
| REQ-INV66-C086 | INV-66 SHALL satisfy: Create concurrency and race-condition tests for shared/distributed Enterprise Wasm control plane state. | WAIVED_PARTIAL | via MC-058 |
| REQ-INV66-C087 | INV-66 SHALL satisfy: Create security tests derived directly from the Enterprise Wasm control plane threat model. | PASS_LOCAL | via MC-037 |
| REQ-INV66-C088 | INV-66 SHALL satisfy: Create benchmark, soak, burst, and fleet-scale tests appropriate to Enterprise Wasm control plane. | PASS_LOCAL | via MC-044 |
| REQ-INV66-C089 | INV-66 SHALL satisfy: Create disaster, partition, reconnect, and degraded-control-plane tests. | WAIVED_PARTIAL | via MC-010, MC-043, MC-059 |
| REQ-INV66-C090 | INV-66 SHALL satisfy: Require machine-readable acceptance evidence before certifying a Enterprise Wasm control plane release for production. | WAIVED_PARTIAL | via MC-001, MC-007, MC-060 |
| REQ-INV66-C091 | INV-66 SHALL satisfy: Define production SLOs, error budgets, and support commitments for Enterprise Wasm control plane. | PASS_LOCAL | Answered by contract.py/component.py (v4.2 conformance design) + 4.3 runtime; pk_core run pending (W-003) |
| REQ-INV66-C092 | INV-66 SHALL satisfy: Define canary, staged rollout, rollback, and emergency-disable procedures for Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-042, MC-061 |
| REQ-INV66-C093 | INV-66 SHALL satisfy: Maintain a supported-version compatibility matrix for Enterprise Wasm control plane and adjacent dependencies. | WAIVED_PARTIAL | via MC-018, MC-057 |
| REQ-INV66-C094 | INV-66 SHALL satisfy: Define patching, vulnerability response, and end-of-life SLAs for Enterprise Wasm control plane. | WAIVED_PARTIAL | via MC-062 |
| REQ-INV66-C095 | INV-66 SHALL satisfy: Provide backup, restore, migration, or reconstruction procedures for Enterprise Wasm control plane state where applicable. | WAIVED_PARTIAL | via MC-005, MC-038, MC-063, MC-070 |
| REQ-INV66-C096 | INV-66 SHALL satisfy: Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. | WAIVED_PARTIAL | via MC-064 |
| REQ-INV66-C097 | INV-66 SHALL satisfy: Define incident severity, paging, escalation, containment, and recovery procedures. | WAIVED_PARTIAL | via MC-003, MC-065 |
| REQ-INV66-C098 | INV-66 SHALL satisfy: Perform recurring access, policy, dependency, configuration, and architecture reviews. | PASS_LOCAL | via MC-025, MC-066 |
| REQ-INV66-C099 | INV-66 SHALL satisfy: Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. | PASS_LOCAL | via MC-067 |
| REQ-INV66-C100 | INV-66 SHALL satisfy: Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. | WAIVED_PARTIAL | via MC-001, MC-007, MC-068 |
