# INV-69 Post-hardening audit — v4.2.0

**Audit date:** 2026-09-22  
**Scope:** repository-local evidence only. External components are not credited as present unless their evidence is included in this archive.

## Verification

- Python compile check: **PASS**.
- Standalone runtime suite: **15/15 PASS** in normal mode.
- Standalone runtime suite: **15/15 PASS** under `python -O`.
- `pk_core` conformance suite: **3 SKIPPED** because `pk_core` is not present/importable in the uploaded archive. This is not counted as certification.

## Defects corrected in 4.2.0

- False README inventory claim: `MASTER.md` was documented as included but was absent.
- The only original test module silently skipped every test when `pk_core` was missing, leaving the local agent runtime unexercised.
- Approval keys used raw `(tool, arg)` set membership, so dict/list arguments could crash with `TypeError`.
- The contract claimed step **and cost** budgets, but only a step budget existed.
- Rejected tool calls did not consume the step budget, allowing unbounded hostile refusal traffic until memory exhaustion.
- Raw tool arguments were persisted in the transcript, creating avoidable secret/PII leakage risk.
- Tool policy metadata was mutable and policy decisions were not serialized for concurrent callers.
- Approvals were not validated against allowlist relevance/side-effect semantics.
- No transcript integrity chain or bounded audit capacity existed.
- Approval state could diverge from audit state if recording failed; v4.2.0 makes approval recording transactional.
- Invalid tool-name types and hostile cyclic/non-finite argument structures could raise instead of failing safely.
- Public interfaces were named but had no included typed schemas.
- Eager package imports made even the local runtime unavailable without `pk_core`.

## Checklist status summary

- **Present:** 12
- **Partial:** 31
- **Missing:** 49
- **External / unverified:** 8

`Partial`, `Missing`, and `External / unverified` entries below are the remaining components/evidence required for a complete production-readiness claim.

## Architecture & Scope

- **INV-69-C005 — PARTIAL:** Document assumptions Agentic workload layer makes about nodes, runtimes, networks, storage, and control planes.  
  Gap: Assumptions are generic; no dependency-specific runtime/network/storage/control-plane assumption matrix.
- **INV-69-C008 — PARTIAL:** Document unsupported deployment patterns and non-goals for Agentic workload layer.  
  Gap: Non-goals exist, but unsupported deployment patterns and prohibited topologies are not enumerated.
- **INV-69-C009 — MISSING:** Assign an accountable owner and escalation path for Agentic workload layer.  
  Gap: No accountable owner, on-call/service owner, or escalation path is defined.

## Requirements & Semantics

- **INV-69-C011 — PARTIAL:** Translate the source function of Agentic workload layer — Major driver for extremely ephemeral sandboxes — into testable SHALL-level requirements.  
  Gap: Mandatory behaviors exist, but there is no numbered SHALL-level requirements specification tied to verification.
- **INV-69-C012 — MISSING:** Define functional requirements for Agentic workload layer across cloud, datacenter, near-edge, and far-edge contexts where applicable.  
  Gap: No cloud/datacenter/near-edge/far-edge requirement profiles or applicability matrix.
- **INV-69-C013 — PARTIAL:** Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.  
  Gap: Three safety SLOs exist, but latency, availability, durability, consistency, determinism and isolation NFRs are not specified where applicable.
- **INV-69-C014 — PARTIAL:** Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Agentic workload layer.  
  Gap: Local outcomes cover ran/pending/refused; system-level success, partial success, degraded, retryable and terminal failure semantics are incomplete.
- **INV-69-C015 — MISSING:** Define lifecycle states and legal state transitions managed or exposed by Agentic workload layer.  
  Gap: No lifecycle state machine or legal transition table for agents/runs/approvals.
- **INV-69-C016 — MISSING:** Define versioning and backward-compatibility requirements for Agentic workload layer.  
  Gap: No supported-version policy, deprecation policy or backward-compatibility contract.
- **INV-69-C017 — PARTIAL:** Define capacity ceilings, quotas, and fairness semantics relevant to Agentic workload layer.  
  Gap: Step/cost/audit bounds now exist; tenant fairness, quota hierarchy and starvation semantics remain undefined.
- **INV-69-C018 — MISSING:** Define behavior when network connectivity is intermittent or absent.  
  Gap: No explicit disconnected/intermittent-network behavior.
- **INV-69-C019 — MISSING:** Define precedence rules when Agentic workload layer requirements conflict with security, residency, SLO, or cost constraints.  
  Gap: No precedence rules for conflicts among security, residency, SLO and cost constraints.
- **INV-69-C020 — MISSING:** Maintain a requirements traceability matrix from each Agentic workload layer requirement to implementation and verification evidence.  
  Gap: No requirements traceability matrix mapping all 100 checks to implementation/tests/evidence.

## Interfaces & Integration

- **INV-69-C021 — PARTIAL:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Agentic workload layer.  
  Gap: Three public audit interfaces are named, but sandbox, identity, authorization, durable-execution and control-plane boundaries are not fully enumerated.
- **INV-69-C023 — EXTERNAL / UNVERIFIED:** Define authentication requirements at each Agentic workload layer boundary.  
  Gap: Authentication is delegated and not specified/tested at each boundary in this repository.
- **INV-69-C024 — PARTIAL:** Define authorization and explicit capability requirements at each Agentic workload layer boundary.  
  Gap: Per-agent allowlists provide local capability checks; distributed/identity-backed authorization requirements are not specified or proven.
- **INV-69-C025 — MISSING:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Agentic workload layer.  
  Gap: No timeout, cancellation, retry, idempotency or backpressure contract for tool and dependency calls.
- **INV-69-C026 — MISSING:** Define structured failure codes and machine-readable error details for Agentic workload layer.  
  Gap: Failures are reason strings, not stable machine-readable error codes/details.
- **INV-69-C027 — MISSING:** Define compatibility behavior when peers use different supported versions.  
  Gap: No mixed-version/upgrade-skew compatibility behavior.
- **INV-69-C028 — PARTIAL:** Document payload, concurrency, queue, connection, or resource limits at Agentic workload layer interfaces.  
  Gap: Step/cost/audit limits exist; payload, queue, connection, concurrency and fan-out limits remain incomplete.
- **INV-69-C029 — PARTIAL:** Provide reference examples and conformance fixtures for Agentic workload layer.  
  Gap: Runtime tests provide examples, but no dedicated reference fixtures or schema conformance corpus.
- **INV-69-C030 — MISSING:** Create automated integration tests proving Agentic workload layer interoperates with adjacent architectural layers.  
  Gap: No automated integration tests with authorization, durable execution, fast sandbox or heavy sandbox layers.

## Implementation & Configuration

- **INV-69-C031 — MISSING:** Select and pin approved implementations, versions, or specifications for Agentic workload layer: Autonomous AI agents, generated code, iterative tool execution.  
  Gap: No implementation/specification lockfile or approved version manifest for adjacent agent/runtime technologies.
- **INV-69-C032 — PARTIAL:** Separate immutable artifacts from mutable configuration and state for Agentic workload layer.  
  Gap: Tool policy metadata is immutable, but immutable-artifact vs mutable-config/state separation is not fully designed.
- **INV-69-C033 — MISSING:** Define declarative configuration and secure defaults for Agentic workload layer.  
  Gap: No declarative configuration file/schema and activation model.
- **INV-69-C034 — PARTIAL:** Validate configuration before activation and fail closed on security-critical errors.  
  Gap: Constructor validation fails closed for local policy fields; there is no full pre-activation config validation pipeline.
- **INV-69-C035 — MISSING:** Support site- and environment-specific configuration without rebuilding immutable artifacts.  
  Gap: No site/environment-specific configuration overlay mechanism.
- **INV-69-C036 — MISSING:** Record configuration provenance, version, author, and activation time.  
  Gap: No configuration provenance record containing version, author and activation time.
- **INV-69-C037 — MISSING:** Apply atomic or transactional configuration updates where partial application is unsafe.  
  Gap: No atomic/transactional configuration update mechanism.
- **INV-69-C038 — PARTIAL:** Define automatic and operator-driven rollback for failed Agentic workload layer changes.  
  Gap: README describes evidence-head rollback conceptually; no executable rollback controller or configuration rollback implementation.
- **INV-69-C040 — PARTIAL:** Provide a deterministic bootstrap path from an empty node/environment to healthy Agentic workload layer operation.  
  Gap: Standalone runtime bootstrap is deterministic; full `pk_core`/adjacent-layer bootstrap is not packaged or pinned here.

## Security, Trust & Isolation

- **INV-69-C041 — PARTIAL:** Threat-model Agentic workload layer against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.  
  Gap: Security model now exists, but lacks a formal threat register with assets, actors, trust zones, likelihood/impact and mitigation ownership.
- **INV-69-C042 — PARTIAL:** Apply least privilege to every identity and capability used by Agentic workload layer.  
  Gap: Local least-privilege tool allowlists exist; identity/capability issuance and least privilege across external dependencies are unverified.
- **INV-69-C043 — EXTERNAL / UNVERIFIED:** Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Agentic workload layer permits.  
  Gap: Ambient filesystem/network/device/kernel/secret authority is a sandbox responsibility and is not implemented or proven here.
- **INV-69-C044 — EXTERNAL / UNVERIFIED:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.  
  Gap: Node/peer/artifact/provider/control-plane authentication is external and unverified in this archive.
- **INV-69-C045 — MISSING:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Agentic workload layer.  
  Gap: No artifact signature, digest/provenance verification or approved-version enforcement.
- **INV-69-C046 — EXTERNAL / UNVERIFIED:** Enforce tenant/workload isolation across Agentic workload layer execution, memory, state, network, and device boundaries as applicable.  
  Gap: Tenant/workload process, memory, state, network and device isolation is delegated to adjacent layers and unverified here.
- **INV-69-C047 — EXTERNAL / UNVERIFIED:** Encrypt sensitive Agentic workload layer data in transit and at rest with managed key rotation.  
  Gap: Transport/storage encryption and managed key rotation are external and unverified.
- **INV-69-C048 — MISSING:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.  
  Gap: No explicit fail-closed/degraded policy for identity, attestation, policy, key or trusted-time outages.
- **INV-69-C049 — PARTIAL:** Emit tamper-evident audit events for security-sensitive Agentic workload layer operations.  
  Gap: Local transcript hash chaining exists, but no durable signed/remote anchor protects against a process owner rewriting both history and head.
- **INV-69-C050 — PARTIAL:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.  
  Gap: Adversarial tests cover allowlist bypass/replay/resource races; spoofing, sandbox escape, side-channel and broader injection coverage is missing.

## Resilience & Failure Handling

- **INV-69-C051 — PARTIAL:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Agentic workload layer.  
  Gap: Contract lists four failure modes; no complete process/VM/node/site/network/provider/control-plane failure inventory.
- **INV-69-C052 — MISSING:** Define automated health and stall detection thresholds for Agentic workload layer.  
  Gap: No health/stall detector thresholds or watchdog design.
- **INV-69-C053 — MISSING:** Implement bounded retry with backoff and jitter only where operations are safe to retry.  
  Gap: No bounded retry/backoff/jitter framework or retry-safety classification.
- **INV-69-C054 — PARTIAL:** Implement admission control, load shedding, or circuit breaking to prevent Agentic workload layer failure cascades.  
  Gap: Budgets provide limited admission control; no load shedding or circuit-breaker behavior for dependency cascades.
- **INV-69-C055 — MISSING:** Define failover behavior without violating isolation, residency, or consistency requirements.  
  Gap: No failover design preserving isolation/residency/consistency.
- **INV-69-C056 — MISSING:** Provide degraded operation when noncritical dependencies are unavailable.  
  Gap: No defined degraded operating modes for noncritical dependency loss.
- **INV-69-C057 — EXTERNAL / UNVERIFIED:** Define crash-consistency, restart, resume, or replay semantics for mutable Agentic workload layer state.  
  Gap: Durable execution is an upstream dependency; crash consistency, resume and replay behavior is not demonstrated here.
- **INV-69-C058 — PARTIAL:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.  
  Gap: One-use approvals reduce local replay; distributed duplicate execution, stale-owner and split-brain protection is not implemented.
- **INV-69-C059 — PARTIAL:** Provide quarantine, freeze, disable, or isolation controls for unsafe Agentic workload layer behavior.  
  Gap: Audit-capacity exhaustion seals the local agent; no operator quarantine/freeze/disable control surface or fleet isolation workflow.
- **INV-69-C060 — MISSING:** Run fault-injection tests proving Agentic workload layer recovery against documented objectives.  
  Gap: No fault-injection suite against documented recovery objectives.

## Performance & Resource Efficiency

- **INV-69-C061 — MISSING:** Establish reproducible baselines for Agentic workload layer latency, throughput, startup, CPU, memory, storage, network, and power overhead.  
  Gap: No reproducible latency/throughput/startup/CPU/memory/storage/network/power baseline.
- **INV-69-C062 — MISSING:** Define p50, p95, p99, and worst-case performance thresholds for Agentic workload layer.  
  Gap: No p50/p95/p99/worst-case thresholds.
- **INV-69-C063 — MISSING:** Measure Agentic workload layer under steady load, burst load, overload, scale-out, scale-in, and recovery.  
  Gap: No steady/burst/overload/scale/recovery performance test suite.
- **INV-69-C064 — MISSING:** Measure per-workload and per-tenant overhead introduced by Agentic workload layer.  
  Gap: No per-workload/per-tenant overhead measurements.
- **INV-69-C065 — MISSING:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Agentic workload layer.  
  Gap: No profiling/evidence for serialization, copies, context switches, network hops or duplicated state.
- **INV-69-C066 — MISSING:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.  
  Gap: No measured optimization plan for locality/caching/batching/zero-copy/kernel bypass.
- **INV-69-C067 — PARTIAL:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.  
  Gap: Step/cost/audit-event growth is bounded; queue depth, buffers, concurrency, memory and fan-out bounds are incomplete.
- **INV-69-C068 — MISSING:** Measure power and thermal impact on constrained edge nodes where relevant.  
  Gap: No edge-node power/thermal measurements or applicability statement.
- **INV-69-C069 — MISSING:** Define capacity models and saturation signals that predict when Agentic workload layer needs more resources.  
  Gap: No capacity model or saturation predictors.
- **INV-69-C070 — MISSING:** Block releases that regress approved Agentic workload layer startup, density, throughput, or tail-latency thresholds.  
  Gap: No performance-regression release gate.

## Observability & Explainability

- **INV-69-C071 — MISSING:** Expose Agentic workload layer health, readiness, version, configuration, dependency status, and active capability set.  
  Gap: No health/readiness/version/configuration/dependency/capability status endpoint or report.
- **INV-69-C072 — PARTIAL:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.  
  Gap: Contract names counters, but there is no metrics emitter/exporter with rate/error/latency/saturation/resource measurements.
- **INV-69-C073 — PARTIAL:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.  
  Gap: Transcript events are structured, but required stable node/tenant/workload/component/operation logging identifiers are incomplete.
- **INV-69-C074 — MISSING:** Propagate trace context across all relevant Agentic workload layer boundaries.  
  Gap: No trace-context propagation.
- **INV-69-C075 — PARTIAL:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.  
  Gap: Raw arguments are excluded from transcript; no high-cardinality diagnostic API, privacy policy or safe detail controls.
- **INV-69-C077 — MISSING:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.  
  Gap: No operator-readable explain view linking decisions to policy/input/topology/constraints.
- **INV-69-C078 — MISSING:** Correlate Agentic workload layer events with application release lineage and the live infrastructure graph.  
  Gap: No release-lineage or live-infrastructure-graph correlation.
- **INV-69-C079 — MISSING:** Define telemetry retention, sampling, privacy, and export policy.  
  Gap: No telemetry retention, sampling, privacy or export policy.
- **INV-69-C080 — MISSING:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.  
  Gap: No dashboards or alert definitions.

## Testing & Certification

- **INV-69-C082 — PARTIAL:** Create contract tests for every public Agentic workload layer interface.  
  Gap: Versioned schemas exist, but there is no automated JSON-Schema validation suite for every public event variant.
- **INV-69-C083 — MISSING:** Create integration tests with every supported adjacent layer and execution tier.  
  Gap: No integration tests across adjacent layers/execution tiers.
- **INV-69-C084 — MISSING:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Agentic workload layer.  
  Gap: No compatibility matrix/tests across CPUs, Python/runtime versions, hypervisors/providers/protocol versions.
- **INV-69-C085 — MISSING:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Agentic workload layer.  
  Gap: No fuzz/property-based test suite for untrusted inputs/schema handlers.
- **INV-69-C087 — PARTIAL:** Create security tests derived directly from the Agentic workload layer threat model.  
  Gap: Security tests cover several local threats; they are not yet systematically generated/traced from a formal threat model.
- **INV-69-C088 — MISSING:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Agentic workload layer.  
  Gap: No benchmark, soak, burst or fleet-scale tests.
- **INV-69-C089 — MISSING:** Create disaster, partition, reconnect, and degraded-control-plane tests.  
  Gap: No disaster/partition/reconnect/degraded-control-plane tests.
- **INV-69-C090 — EXTERNAL / UNVERIFIED:** Require machine-readable acceptance evidence before certifying a Agentic workload layer release for production.  
  Gap: Machine-readable acceptance evidence depends on `pk_core`; it is absent from this archive and the conformance suite skips here.

## Operations, Release & Governance

- **INV-69-C091 — PARTIAL:** Define production SLOs, error budgets, and support commitments for Agentic workload layer.  
  Gap: Three safety SLOs are declared; availability/performance support commitments and operational error budgets are incomplete.
- **INV-69-C092 — PARTIAL:** Define canary, staged rollout, rollback, and emergency-disable procedures for Agentic workload layer.  
  Gap: Rollback/emergency-disable are described at a high level; no canary/staged rollout implementation or executable rollback runbook.
- **INV-69-C093 — MISSING:** Maintain a supported-version compatibility matrix for Agentic workload layer and adjacent dependencies.  
  Gap: No supported-version compatibility matrix for this component and adjacent dependencies.
- **INV-69-C094 — MISSING:** Define patching, vulnerability response, and end-of-life SLAs for Agentic workload layer.  
  Gap: No patching/vulnerability-response/EOL SLA.
- **INV-69-C095 — MISSING:** Provide backup, restore, migration, or reconstruction procedures for Agentic workload layer state where applicable.  
  Gap: No backup/restore/migration/reconstruction procedure for transcript/approval state where persistence is introduced.
- **INV-69-C096 — PARTIAL:** Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.  
  Gap: README has day-0/1/2 guidance, but not a production-grade procedural runbook with prerequisites, commands, expected outputs and rollback.
- **INV-69-C097 — MISSING:** Define incident severity, paging, escalation, containment, and recovery procedures.  
  Gap: No incident severity model, paging/escalation/containment/recovery runbook.
- **INV-69-C098 — MISSING:** Perform recurring access, policy, dependency, configuration, and architecture reviews.  
  Gap: No recurring access/policy/dependency/configuration/architecture review schedule or evidence template.
- **INV-69-C099 — MISSING:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.  
  Gap: No exception/waiver/technical-debt/deprecation register with owners and expiries.
- **INV-69-C100 — EXTERNAL / UNVERIFIED:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.  
  Gap: Formal exit gate is delegated to `pk_core`; no executable gate result/evidence is included or verifiable in this archive.

## Present controls/evidence

- **INV-69-C001:** `contract.py` defines responsibility.
- **INV-69-C002:** `contract.py` defines owns/not_owns.
- **INV-69-C003:** `contract.py` lists INV-57/59/70/71 dependencies.
- **INV-69-C004:** `contract.py` names the transcript as source of truth.
- **INV-69-C006:** `contract.py` defines tenant/environment/site/workload boundaries.
- **INV-69-C007:** `contract.py` separates mandatory and optional capabilities.
- **INV-69-C010:** `docs/ADR-0001-agent-execution-governance.md` records the architecture decision.
- **INV-69-C022:** Three versioned JSON Schemas are included under `schemas/`.
- **INV-69-C039:** Runtime transcript stores opaque argument references/shapes rather than raw argument values; security doc prohibits secret persistence.
- **INV-69-C076:** Every local policy decision event includes a reason.
- **INV-69-C081:** `tests/test_runtime.py` contains deterministic standard-library unit/security tests.
- **INV-69-C086:** Concurrency test verifies per-agent locking and step-budget race behavior.

## Production-readiness conclusion

Version 4.2.0 materially improves the local reference kernel, its testability, audit privacy/integrity and interface documentation. It is **not** a self-contained production-certified agentic workload layer: the archive still lacks substantial distributed-systems, operational, performance, integration and governance evidence, and the external `pk_core` gate cannot be executed from this archive alone.
