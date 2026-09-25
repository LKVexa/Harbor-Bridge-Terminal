# Missing Components - INV-35 v4.2.0

This is the post-update missing-component inventory. It treats both **missing** and **partial** checklist items as open work; a partial item has some evidence but still lacks a required production component.

**Checklist status:** 8 present, 23 partial, 69 missing (92 open requirements).

## Architecture & Scope

- **INV-35-C005 — PARTIAL:** Expanded environment/runtime/network/storage/control-plane assumptions specification
- **INV-35-C009 — MISSING:** OWNERS/CODEOWNERS and escalation policy
- **INV-35-C010 — MISSING:** Approved ADR for Nexus/high-performance VM I/O architecture

## Requirements & Semantics

- **INV-35-C011 — PARTIAL:** Normative SHALL-level requirements specification
- **INV-35-C012 — MISSING:** Cloud/datacenter/near-edge/far-edge deployment behavior profiles
- **INV-35-C013 — PARTIAL:** Complete non-functional requirements and tail-latency/availability/isolation targets
- **INV-35-C014 — MISSING:** Success/degraded/retryable/terminal failure semantics
- **INV-35-C015 — MISSING:** Lifecycle state machine and legal transitions
- **INV-35-C016 — MISSING:** Versioning and backward-compatibility policy
- **INV-35-C017 — PARTIAL:** Quota/fairness/capacity model beyond local queue bounds
- **INV-35-C018 — MISSING:** Intermittent/offline network behavior statement
- **INV-35-C019 — MISSING:** Security/residency/SLO/cost precedence policy
- **INV-35-C020 — PARTIAL:** Full requirement-to-implementation-to-verification traceability matrix

## Interfaces & Integration

- **INV-35-C021 — PARTIAL:** Complete boundary inventory including device/hypervisor/control-plane boundaries
- **INV-35-C022 — PARTIAL:** Machine-readable typed schema definitions for public interfaces
- **INV-35-C023 — MISSING:** Boundary authentication policy
- **INV-35-C024 — MISSING:** Authorization/capability model
- **INV-35-C025 — MISSING:** Timeout/cancellation/retry/idempotency/backpressure contract
- **INV-35-C026 — MISSING:** Stable machine-readable error-code schema
- **INV-35-C027 — MISSING:** Peer-version negotiation and compatibility behavior
- **INV-35-C028 — PARTIAL:** Published interface/resource limits specification
- **INV-35-C029 — PARTIAL:** Reference examples plus reusable conformance fixtures
- **INV-35-C030 — MISSING:** Automated integration tests with adjacent architectural layers

## Implementation & Configuration

- **INV-35-C031 — MISSING:** Pinned approved Nexus implementation/specification manifest
- **INV-35-C032 — MISSING:** Immutable-artifact versus mutable-config/state layout
- **INV-35-C033 — MISSING:** Declarative configuration schema with secure defaults
- **INV-35-C034 — MISSING:** Pre-activation configuration validation/fail-closed loader
- **INV-35-C035 — MISSING:** Site/environment override mechanism without rebuilds
- **INV-35-C036 — MISSING:** Configuration provenance/audit metadata
- **INV-35-C037 — MISSING:** Atomic/transactional configuration update mechanism
- **INV-35-C038 — MISSING:** Configuration rollback mechanism and procedure
- **INV-35-C039 — MISSING:** Secrets handling/redaction policy and enforcement
- **INV-35-C040 — PARTIAL:** Pinned dependency/bootstrap manifest for pk_core and supported Python

## Security, Trust & Isolation

- **INV-35-C041 — PARTIAL:** Formal threat model covering all mandated attacker classes
- **INV-35-C042 — MISSING:** Least-privilege identity/capability design
- **INV-35-C043 — MISSING:** Ambient-authority elimination/sandbox policy
- **INV-35-C044 — MISSING:** Node/peer/artifact/provider/control-plane authentication
- **INV-35-C045 — MISSING:** Artifact signature/digest/provenance verification
- **INV-35-C046 — PARTIAL:** Complete tenant/workload isolation design across execution/state/network/device boundaries
- **INV-35-C047 — MISSING:** Encryption and key-rotation policy for sensitive payloads/metadata
- **INV-35-C048 — MISSING:** Safe behavior when identity/attestation/policy/key/time services fail
- **INV-35-C049 — MISSING:** Tamper-evident security audit event pipeline
- **INV-35-C050 — PARTIAL:** Complete adversarial suite: privilege escalation, injection, replay, spoofing, escape, side channels, exhaustion

## Resilience & Failure Handling

- **INV-35-C051 — PARTIAL:** Full failure-mode/FMEA catalogue across process/VM/node/site/network/provider/control plane
- **INV-35-C052 — MISSING:** Automated health and stall detection thresholds
- **INV-35-C053 — MISSING:** Bounded retry/backoff/jitter policy where retry is safe
- **INV-35-C054 — PARTIAL:** Explicit overload/load-shedding/circuit-breaker behavior beyond queue refusal
- **INV-35-C055 — MISSING:** Failover behavior and invariant preservation
- **INV-35-C056 — MISSING:** Defined degraded-operation modes
- **INV-35-C057 — MISSING:** Crash-consistency/restart/resume/replay semantics
- **INV-35-C058 — MISSING:** Split-brain/duplicate-owner/stale-controller protections or explicit non-applicability proof
- **INV-35-C059 — PARTIAL:** Runtime quarantine/freeze/disable control, not only registry removal
- **INV-35-C060 — MISSING:** Fault-injection harness and recovery-objective tests

## Performance & Resource Efficiency

- **INV-35-C061 — MISSING:** Reproducible latency/throughput/startup/CPU/memory/storage/network/power benchmark baseline
- **INV-35-C062 — MISSING:** p50/p95/p99/worst-case performance thresholds
- **INV-35-C063 — MISSING:** Steady/burst/overload/scale/recovery benchmark matrix
- **INV-35-C064 — MISSING:** Per-workload/per-tenant overhead measurements
- **INV-35-C065 — MISSING:** Datapath copy/serialization/context-switch/hop analysis
- **INV-35-C066 — MISSING:** Measured optimization implementation (batching/zero-copy/kernel bypass where valid)
- **INV-35-C067 — PARTIAL:** Complete resource-bound model including buffers/concurrency/fan-out
- **INV-35-C068 — MISSING:** Power/thermal characterization for constrained edge nodes
- **INV-35-C069 — MISSING:** Capacity model and saturation signals
- **INV-35-C070 — MISSING:** Automated performance-regression release gate

## Observability & Explainability

- **INV-35-C071 — MISSING:** Health/readiness/version/config/dependency/capability status surface
- **INV-35-C072 — MISSING:** Structured metrics implementation
- **INV-35-C073 — MISSING:** Structured logging with stable correlation identifiers
- **INV-35-C074 — MISSING:** Trace-context propagation
- **INV-35-C075 — MISSING:** Safe high-cardinality diagnostics and redaction controls
- **INV-35-C076 — MISSING:** Structured reason recording for automated decisions
- **INV-35-C077 — MISSING:** Operator explain view
- **INV-35-C078 — MISSING:** Release-lineage/infrastructure-graph correlation
- **INV-35-C079 — MISSING:** Telemetry retention/sampling/privacy/export policy
- **INV-35-C080 — MISSING:** Dashboards and differentiated alerting

## Testing & Certification

- **INV-35-C082 — PARTIAL:** Contract tests backed by actual schema artifacts for every public interface
- **INV-35-C083 — MISSING:** Integration tests for every supported adjacent layer/tier
- **INV-35-C084 — MISSING:** CPU/runtime/hypervisor/provider/protocol compatibility test matrix
- **INV-35-C085 — MISSING:** Fuzz/property-based testing of untrusted descriptor/schema inputs
- **INV-35-C086 — PARTIAL:** Expanded concurrency/race/stress testing under submit/complete contention
- **INV-35-C087 — PARTIAL:** Threat-model-complete security test suite
- **INV-35-C088 — MISSING:** Benchmark/soak/burst/fleet-scale test harness
- **INV-35-C089 — MISSING:** Disaster/partition/reconnect/degraded-control-plane tests or explicit applicability rationale
- **INV-35-C090 — MISSING:** Machine-readable signed/sealed acceptance evidence generated by a release gate

## Operations, Release & Governance

- **INV-35-C091 — PARTIAL:** Complete production SLO/error-budget/support commitment document
- **INV-35-C092 — PARTIAL:** Detailed canary/staged-rollout/rollback/emergency-disable procedures
- **INV-35-C093 — MISSING:** Supported-version compatibility matrix for adjacent dependencies
- **INV-35-C094 — MISSING:** Patching/vulnerability-response/end-of-life SLAs
- **INV-35-C095 — MISSING:** Backup/restore/migration/reconstruction procedure or explicit statelessness decision
- **INV-35-C096 — PARTIAL:** Full day-0/day-1/day-2 operational runbooks
- **INV-35-C097 — MISSING:** Incident severity/paging/escalation/containment/recovery procedure
- **INV-35-C098 — MISSING:** Recurring access/policy/dependency/configuration/architecture review schedule
- **INV-35-C099 — MISSING:** Exception/waiver/technical-debt/deprecation register with owners and expiry
- **INV-35-C100 — MISSING:** Formal production exit gate with auditable acceptance criteria

## Additional repository-level omissions not represented as standalone checklist rows

- **License file:** no `LICENSE`/`NOTICE` is present, so redistribution terms are not defined by this archive.
- **Pinned dependency manifest:** no `pyproject.toml`, lock file, vendored dependency metadata, or approved `pk_core` version pin is present.
- **CI configuration:** no GitHub Actions/Azure DevOps/GitLab/Jenkins workflow is present to execute `verify.py` on change.
- **Static-analysis configuration:** no configured linter, type checker, SAST rule set, dependency scanner, or secret scanner is present.
- **Schema directory:** public interface identifiers exist, but no JSON Schema/Protobuf/WIT/IDL artifacts are present.
- **Evidence/conformance outputs:** no sealed `evidence/` ledger or generated `conformance/PK_GATE_RESULTS.json` ships in the archive.
- **Benchmark assets:** no benchmark harness, baseline data, reproducibility metadata, or regression thresholds ship in the archive.
- **Fuzz corpus/property tests:** no fuzz target, seed corpus, mutation strategy, or property-based test configuration is present.
- **Operational telemetry assets:** no dashboard, alert rules, log schema, metric exposition implementation, or trace configuration is present.
- **Supply-chain artifacts:** no SBOM, provenance statement, signature verification policy, artifact digest manifest, or release attestation is present.
- **Ownership/governance metadata:** no CODEOWNERS/OWNERS file, support contact, security contact, exception register, or EOL policy is present.

## Highest-risk blockers

1. Full verification depends on an unspecified external `pk_core`; without an approved version pin the certification path is not reproducible.
2. Public interface names are versioned, but the repository has no machine-readable interface schemas or stable error model.
3. The threat model and adversarial testing are incomplete for a guest/host trust boundary.
4. There is no production telemetry implementation or performance evidence for a component explicitly labeled high-performance.
5. There is no integration/compatibility/fault/fuzz/soak certification suite against actual hypervisor, virtio/vhost, backend, or adjacent-layer implementations.
6. There is no formal release gate evidence, ownership/escalation policy, or incident/runbook package.
