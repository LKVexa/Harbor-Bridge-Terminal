# Audit report — INV-45 SFI mechanisms v4.2.0

## Scope and result

The uploaded 4.1.0 repository was parsed, statically audited, hardened, version-bumped to 4.2.0, and re-audited. The audit distinguishes reference-model correctness from production checklist completion. The archive compiles and its standalone SFI core tests pass in normal and optimized Python modes; the external `pk_core` production gate remains unverified because that dependency is not included.

## High-impact defects fixed

- Checklist evidence was misindexed: unrelated runtime behavior was being written into C036 (configuration provenance), C043 (ambient authority), C047 (encryption), C051 and C057. These false-positive overrides were removed; concrete isolation evidence is now attached only to C046.
- Verification previously sealed only the `accesses` object identity. The region and indirect-target policy could be replaced after verification without invalidating the module. 4.2.0 seals all security-sensitive state.
- Caller-provided mutable collections could undermine the intent of verification. 4.2.0 normalizes access manifests and target sets into immutable copies.
- A failed re-verification could leave an earlier verification flag/snapshot alive. 4.2.0 invalidates before checking the new state.
- Core input types and values were weakly validated. 4.2.0 rejects malformed region values, access records, targets, names and non-finite/negative overhead metadata.
- Public security errors had no stable machine-readable code/details. 4.2.0 adds a structured error base and codes.
- Runtime report schema identifiers existed only as strings. 4.2.0 adds JSON Schema documents and tests that bind them to runtime schema IDs.
- The README claimed `MASTER.md` was present although it was absent. 4.2.0 removes the claim and records the artifact as missing.

## Validation performed

- `python -m compileall` — PASS.
- `python tests/test_sfi_core.py` — 11/11 PASS.
- `python -O tests/test_sfi_core.py` — 11/11 PASS.
- `tests/test_component.py` — syntactically runnable but 3/3 integration tests SKIP without `pk_core`; this is not counted as a production pass.
- Minimal local stub harness — component import, contract construction, and implementation/security/resilience assessment methods execute without indexing/runtime errors.
- Runtime-source bare-`assert` scan — none found outside tests.

## 100-item evidence re-audit

**Summary:** 7 implemented / 29 partial / 64 missing.

| Check | Status | Requirement |
|---|---|---|
| INV-45-C001 | implemented | Define the exact production responsibility of SFI mechanisms. |
| INV-45-C002 | implemented | Document what SFI mechanisms owns and explicitly does not own. |
| INV-45-C003 | implemented | Identify upstream, downstream, and peer dependencies of SFI mechanisms. |
| INV-45-C004 | implemented | Define the authoritative source of truth used by SFI mechanisms. |
| INV-45-C005 | partial | Document assumptions SFI mechanisms makes about nodes, runtimes, networks, storage, and control planes. |
| INV-45-C006 | implemented | Define tenant, environment, site, and workload boundaries relevant to SFI mechanisms. |
| INV-45-C007 | implemented | Separate mandatory SFI mechanisms capabilities from optional optimizations. |
| INV-45-C008 | partial | Document unsupported deployment patterns and non-goals for SFI mechanisms. |
| INV-45-C009 | missing | Assign an accountable owner and escalation path for SFI mechanisms. |
| INV-45-C010 | missing | Approve an architecture decision record for SFI mechanisms, its technologies (Linear block partitioning, heap masking, pinned base registers, shadow stacks, code-page ASLR), and its function (Strengthen multi-tenant Wasm execution). |
| INV-45-C011 | partial | Translate the source function of SFI mechanisms — Strengthen multi-tenant Wasm execution — into testable SHALL-level requirements. |
| INV-45-C012 | missing | Define functional requirements for SFI mechanisms across cloud, datacenter, near-edge, and far-edge contexts where applicable. |
| INV-45-C013 | partial | Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable. |
| INV-45-C014 | missing | Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for SFI mechanisms. |
| INV-45-C015 | missing | Define lifecycle states and legal state transitions managed or exposed by SFI mechanisms. |
| INV-45-C016 | partial | Define versioning and backward-compatibility requirements for SFI mechanisms. |
| INV-45-C017 | missing | Define capacity ceilings, quotas, and fairness semantics relevant to SFI mechanisms. |
| INV-45-C018 | missing | Define behavior when network connectivity is intermittent or absent. |
| INV-45-C019 | missing | Define precedence rules when SFI mechanisms requirements conflict with security, residency, SLO, or cost constraints. |
| INV-45-C020 | missing | Maintain a requirements traceability matrix from each SFI mechanisms requirement to implementation and verification evidence. |
| INV-45-C021 | partial | Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by SFI mechanisms. |
| INV-45-C022 | partial | Use versioned typed schemas for all externally visible SFI mechanisms contracts. |
| INV-45-C023 | missing | Define authentication requirements at each SFI mechanisms boundary. |
| INV-45-C024 | missing | Define authorization and explicit capability requirements at each SFI mechanisms boundary. |
| INV-45-C025 | missing | Define timeout, cancellation, retry, idempotency, and backpressure semantics for SFI mechanisms. |
| INV-45-C026 | partial | Define structured failure codes and machine-readable error details for SFI mechanisms. |
| INV-45-C027 | missing | Define compatibility behavior when peers use different supported versions. |
| INV-45-C028 | missing | Document payload, concurrency, queue, connection, or resource limits at SFI mechanisms interfaces. |
| INV-45-C029 | partial | Provide reference examples and conformance fixtures for SFI mechanisms. |
| INV-45-C030 | missing | Create automated integration tests proving SFI mechanisms interoperates with adjacent architectural layers. |
| INV-45-C031 | partial | Select and pin approved implementations, versions, or specifications for SFI mechanisms: Linear block partitioning, heap masking, pinned base registers, shadow stacks, code-page ASLR. |
| INV-45-C032 | partial | Separate immutable artifacts from mutable configuration and state for SFI mechanisms. |
| INV-45-C033 | missing | Define declarative configuration and secure defaults for SFI mechanisms. |
| INV-45-C034 | partial | Validate configuration before activation and fail closed on security-critical errors. |
| INV-45-C035 | missing | Support site- and environment-specific configuration without rebuilding immutable artifacts. |
| INV-45-C036 | missing | Record configuration provenance, version, author, and activation time. |
| INV-45-C037 | missing | Apply atomic or transactional configuration updates where partial application is unsafe. |
| INV-45-C038 | partial | Define automatic and operator-driven rollback for failed SFI mechanisms changes. |
| INV-45-C039 | partial | Keep credentials and secret material out of ordinary SFI mechanisms configuration and diagnostics. |
| INV-45-C040 | partial | Provide a deterministic bootstrap path from an empty node/environment to healthy SFI mechanisms operation. |
| INV-45-C041 | partial | Threat-model SFI mechanisms against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse. |
| INV-45-C042 | missing | Apply least privilege to every identity and capability used by SFI mechanisms. |
| INV-45-C043 | partial | Eliminate ambient filesystem, network, device, kernel, and secret authority wherever SFI mechanisms permits. |
| INV-45-C044 | missing | Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted. |
| INV-45-C045 | missing | Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by SFI mechanisms. |
| INV-45-C046 | partial | Enforce tenant/workload isolation across SFI mechanisms execution, memory, state, network, and device boundaries as applicable. |
| INV-45-C047 | missing | Encrypt sensitive SFI mechanisms data in transit and at rest with managed key rotation. |
| INV-45-C048 | missing | Define safe behavior when identity, attestation, policy, key, or time services are unavailable. |
| INV-45-C049 | missing | Emit tamper-evident audit events for security-sensitive SFI mechanisms operations. |
| INV-45-C050 | partial | Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion. |
| INV-45-C051 | partial | Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting SFI mechanisms. |
| INV-45-C052 | missing | Define automated health and stall detection thresholds for SFI mechanisms. |
| INV-45-C053 | missing | Implement bounded retry with backoff and jitter only where operations are safe to retry. |
| INV-45-C054 | missing | Implement admission control, load shedding, or circuit breaking to prevent SFI mechanisms failure cascades. |
| INV-45-C055 | missing | Define failover behavior without violating isolation, residency, or consistency requirements. |
| INV-45-C056 | missing | Provide degraded operation when noncritical dependencies are unavailable. |
| INV-45-C057 | missing | Define crash-consistency, restart, resume, or replay semantics for mutable SFI mechanisms state. |
| INV-45-C058 | missing | Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant. |
| INV-45-C059 | partial | Provide quarantine, freeze, disable, or isolation controls for unsafe SFI mechanisms behavior. |
| INV-45-C060 | missing | Run fault-injection tests proving SFI mechanisms recovery against documented objectives. |
| INV-45-C061 | missing | Establish reproducible baselines for SFI mechanisms latency, throughput, startup, CPU, memory, storage, network, and power overhead. |
| INV-45-C062 | missing | Define p50, p95, p99, and worst-case performance thresholds for SFI mechanisms. |
| INV-45-C063 | missing | Measure SFI mechanisms under steady load, burst load, overload, scale-out, scale-in, and recovery. |
| INV-45-C064 | missing | Measure per-workload and per-tenant overhead introduced by SFI mechanisms. |
| INV-45-C065 | missing | Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in SFI mechanisms. |
| INV-45-C066 | missing | Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit. |
| INV-45-C067 | missing | Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out. |
| INV-45-C068 | missing | Measure power and thermal impact on constrained edge nodes where relevant. |
| INV-45-C069 | missing | Define capacity models and saturation signals that predict when SFI mechanisms needs more resources. |
| INV-45-C070 | missing | Block releases that regress approved SFI mechanisms startup, density, throughput, or tail-latency thresholds. |
| INV-45-C071 | partial | Expose SFI mechanisms health, readiness, version, configuration, dependency status, and active capability set. |
| INV-45-C072 | partial | Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use. |
| INV-45-C073 | missing | Emit structured logs with stable node, tenant, workload, component, and operation identifiers. |
| INV-45-C074 | missing | Propagate trace context across all relevant SFI mechanisms boundaries. |
| INV-45-C075 | missing | Expose high-cardinality diagnostic detail safely without leaking tenant or secret data. |
| INV-45-C076 | partial | Record the reason for every automated decision made by SFI mechanisms. |
| INV-45-C077 | missing | Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints. |
| INV-45-C078 | missing | Correlate SFI mechanisms events with application release lineage and the live infrastructure graph. |
| INV-45-C079 | missing | Define telemetry retention, sampling, privacy, and export policy. |
| INV-45-C080 | missing | Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect. |
| INV-45-C081 | implemented | Create unit tests for deterministic SFI mechanisms logic and state transitions. |
| INV-45-C082 | partial | Create contract tests for every public SFI mechanisms interface. |
| INV-45-C083 | missing | Create integration tests with every supported adjacent layer and execution tier. |
| INV-45-C084 | missing | Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to SFI mechanisms. |
| INV-45-C085 | missing | Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by SFI mechanisms. |
| INV-45-C086 | missing | Create concurrency and race-condition tests for shared/distributed SFI mechanisms state. |
| INV-45-C087 | partial | Create security tests derived directly from the SFI mechanisms threat model. |
| INV-45-C088 | missing | Create benchmark, soak, burst, and fleet-scale tests appropriate to SFI mechanisms. |
| INV-45-C089 | missing | Create disaster, partition, reconnect, and degraded-control-plane tests. |
| INV-45-C090 | missing | Require machine-readable acceptance evidence before certifying a SFI mechanisms release for production. |
| INV-45-C091 | partial | Define production SLOs, error budgets, and support commitments for SFI mechanisms. |
| INV-45-C092 | partial | Define canary, staged rollout, rollback, and emergency-disable procedures for SFI mechanisms. |
| INV-45-C093 | missing | Maintain a supported-version compatibility matrix for SFI mechanisms and adjacent dependencies. |
| INV-45-C094 | missing | Define patching, vulnerability response, and end-of-life SLAs for SFI mechanisms. |
| INV-45-C095 | missing | Provide backup, restore, migration, or reconstruction procedures for SFI mechanisms state where applicable. |
| INV-45-C096 | partial | Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks. |
| INV-45-C097 | missing | Define incident severity, paging, escalation, containment, and recovery procedures. |
| INV-45-C098 | missing | Perform recurring access, policy, dependency, configuration, and architecture reviews. |
| INV-45-C099 | missing | Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates. |
| INV-45-C100 | missing | Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness. |

See `MISSING_COMPONENTS.md` for the grouped remediation ledger and `CHECKLIST_AUDIT.json` for the machine-readable status set.
