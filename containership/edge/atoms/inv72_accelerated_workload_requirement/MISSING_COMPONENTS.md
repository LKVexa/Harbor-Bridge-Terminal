> **Historical (v4.2.0).** Superseded by `POST_REMEDIATION_AUDIT.md` and `evidence/RTM.json` in v4.3.0; kept unchanged below as the baseline the professional checklist was written against.

# Missing Components — INV-72 v4.2.0

Post-hardening audit of the supplied standalone repository. This report is intentionally conservative: framework defaults, undocumented operator behavior, and external systems are not counted as implemented evidence.

## Status summary

| Status | Count | Meaning |
|---|---:|---|
| Implemented locally | 9 | Concrete repository-local evidence was found. |
| Partial | 24 | Some local evidence exists, but the checklist requirement is incomplete. |
| Missing | 65 | No sufficient local implementation/evidence was found. |
| Unverified external | 2 | The repository delegates the control to unavailable external `pk_core` behavior/evidence. |

## Repository-level missing components

- **External integration dependency package/lock:** `pk_core` is required by `component.py` and `contract.py` but was not included or version-pinned.
- **Packaging manifest:** no `pyproject.toml`, wheel/sdist configuration, or declared Python/dependency compatibility exists.
- **License artifact:** no repository license file is present.
- **CI/release automation:** no CI workflow, quality gate, reproducible build, artifact signing, or release pipeline is present.
- **Architecture/governance artifacts:** no ADR, accountable owner/escalation record, exception register, compatibility matrix, or formal production gate artifact is present.
- **Security program artifacts:** no full threat model, security policy, SBOM/provenance verification, vulnerability-response SLA, or tamper-evident audit implementation is present.
- **Machine-readable interface schemas:** no versioned schema files for requirements, inventory, successful decisions, or structured refusal/error payloads are present.
- **Production configuration/deployment assets:** no declarative config schema, environment overlays, deployment manifests, rollback automation, or secret-management integration exists.
- **Observability assets:** no metrics exporter, structured logging, tracing, dashboard, alert, retention, or privacy configuration is implemented.
- **Resilience assets:** no health/stall detection, admission control, circuit breaker, failover, degraded mode, quarantine, persistence/recovery, or fault-injection harness exists.
- **Performance certification assets:** no benchmark baseline, load/soak/fleet tests, capacity model, power/thermal evidence, or regression gate exists.
- **Cross-layer certification:** adjacent GAP-02, GAP-11, INV-68, and INV-69 implementations were not included, so their interoperability is unverified.
- **Acceptance evidence:** no generated `pk_core` evidence ledger or `PK_GATE_RESULTS.json` was supplied.

## Architecture & Scope

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C009 | Missing | No accountable owner or escalation path is named in the repository. |
| INV-72-C010 | Missing | No approved architecture decision record (ADR) for GPU passthrough/local inference is present. |

## Requirements & Semantics

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C011 | Partial | Mandatory capabilities exist, but there is no complete SHALL-level requirements specification mapped to tests. |
| INV-72-C012 | Missing | No cloud/datacenter/near-edge/far-edge applicability and behavior matrix is defined. |
| INV-72-C013 | Partial | The contract declares limited SLOs, but availability, durability, consistency/determinism applicability and evidence are incomplete. |
| INV-72-C014 | Partial | A few failure modes are listed, but success/partial/degraded/retryable/terminal semantics are not defined comprehensively. |
| INV-72-C015 | Missing | No lifecycle state model or legal transition table exists. |
| INV-72-C016 | Partial | Semantic version files exist, but backward-compatibility and deprecation policy are not defined. |
| INV-72-C017 | Missing | No capacity ceilings, tenant quotas, or fairness policy is defined. |
| INV-72-C018 | Missing | No explicit intermittent/offline network behavior is documented for dependencies or integration paths. |
| INV-72-C019 | Missing | No precedence policy resolves security, residency, SLO, and cost conflicts. |
| INV-72-C020 | Missing | No requirements-to-implementation-to-verification traceability matrix is present. |

## Interfaces & Integration

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C021 | Partial | The local request/inventory/match surfaces are documented, but there is no exhaustive boundary inventory covering every integration/control-plane edge. |
| INV-72-C022 | Partial | `Device` is typed, but request/match contracts do not have versioned machine-readable schemas. |
| INV-72-C023 | Missing | No authentication requirements are defined for external boundaries. |
| INV-72-C024 | Missing | No authorization/capability model is defined for external boundaries. |
| INV-72-C025 | Missing | No timeout, cancellation, retry, idempotency, or backpressure contract exists for integration calls. |
| INV-72-C026 | Partial | Explicit validation exception classes exist, but refusal reasons are free-form strings with no stable error codes or structured detail schema. |
| INV-72-C027 | Missing | No mixed-version peer compatibility rules are documented or tested. |
| INV-72-C028 | Missing | No upper bounds for payload size, inventory size, count, concurrency, queues, connections, or fan-out are defined. |
| INV-72-C029 | Partial | Unit tests provide examples, but no dedicated versioned conformance fixture set is present. |
| INV-72-C030 | Missing | No automated tests exercise GAP-02, GAP-11, INV-68, or INV-69 integration. |

## Implementation & Configuration

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C031 | Missing | No approved/pinned GPU passthrough, local-inference, driver, runtime, or specification versions are declared. |
| INV-72-C032 | Missing | No explicit immutable-artifact versus mutable-configuration/state architecture is documented. |
| INV-72-C033 | Partial | The matcher has a secure isolation default, but no declarative configuration model or configuration artifact exists. |
| INV-72-C034 | Missing | Request/inventory inputs are validated fail-closed, but there is no configuration activation/validation path. |
| INV-72-C035 | Missing | No site/environment configuration overlay mechanism exists. |
| INV-72-C036 | Missing | No configuration provenance fields or activation audit record exists. |
| INV-72-C037 | Missing | No atomic/transactional configuration update mechanism exists. |
| INV-72-C038 | Missing | No automated/operator configuration rollback mechanism exists. |
| INV-72-C039 | Partial | No secrets are used by the matcher, but there is no repository-level secret handling/redaction policy or enforcement. |
| INV-72-C040 | Partial | Local test commands are deterministic, but a clean bootstrap cannot be completed from the archive alone because `pk_core` is external and unpinned. |

## Security, Trust & Isolation

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C041 | Partial | The contract lists three threats, but no full threat model covers malicious tenants, compromised workloads, hostile inputs, supply chain, and control-plane abuse. |
| INV-72-C042 | Missing | No identity/capability inventory or least-privilege policy exists. |
| INV-72-C043 | Partial | The pure matcher has no direct filesystem/network/kernel/secret authority, but the external integration runtime is not included or assessed. |
| INV-72-C044 | Missing | No node/peer/artifact/provider/control-plane authentication implementation is present. |
| INV-72-C045 | Missing | No signature, digest, provenance, SBOM, or approved-artifact verification pipeline is present. |
| INV-72-C046 | Partial | Partition and cross-tenant device checks exist, but execution, memory, state, network, and device isolation are not end-to-end enforced here. |
| INV-72-C047 | Missing | No transport/storage encryption or key-rotation implementation/policy is present. |
| INV-72-C048 | Missing | No fail-closed behavior is defined for unavailable identity, attestation, policy, key, or time services. |
| INV-72-C049 | Missing | No tamper-evident audit event stream is implemented. |
| INV-72-C050 | Missing | No comprehensive adversarial security suite covers privilege escalation, injection, replay, spoofing, escape, side channels, and exhaustion. |

## Resilience & Failure Handling

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C051 | Partial | The contract lists several direct matching failures, but not process/VM/node/site/network/provider/control-plane failure scenarios. |
| INV-72-C052 | Missing | No health/stall detector or threshold definitions are implemented. |
| INV-72-C053 | Missing | No retry policy with bounded backoff/jitter is defined for external dependencies; no explicit N/A rationale is recorded for the pure matcher. |
| INV-72-C054 | Missing | No admission control, load shedding, or circuit breaker exists. |
| INV-72-C055 | Missing | No failover policy constrained by isolation/residency/consistency exists. |
| INV-72-C056 | Missing | No degraded-mode behavior is defined for noncritical dependency loss. |
| INV-72-C057 | Missing | The in-memory tenant ownership model has no crash-consistency, restart, resume, replay, or durability semantics. |
| INV-72-C058 | Partial | Duplicate device IDs are now rejected locally, but distributed duplicate ownership, stale-controller, and split-brain protection is absent. |
| INV-72-C059 | Missing | No quarantine/freeze/disable/isolation control surface exists for unsafe behavior. |
| INV-72-C060 | Missing | No fault-injection recovery test suite exists. |

## Performance & Resource Efficiency

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C061 | Missing | No reproducible performance/resource baseline suite exists. |
| INV-72-C062 | Partial | The contract declares a p99 match target, but p50/p95/worst-case thresholds and measured evidence are absent. |
| INV-72-C063 | Missing | No steady/burst/overload/scale/recovery performance testing exists. |
| INV-72-C064 | Missing | No per-workload or per-tenant overhead measurements exist. |
| INV-72-C065 | Missing | No serialization/copy/context-switch/network-hop/duplicate-state efficiency analysis exists. |
| INV-72-C066 | Missing | No measured optimization work (locality/caching/batching/zero-copy/kernel bypass) is documented. |
| INV-72-C067 | Missing | No hard bounds on inventory size, count, memory growth, concurrency, queue depth, buffers, or fan-out are defined. |
| INV-72-C068 | Missing | No edge-node power or thermal measurements exist. |
| INV-72-C069 | Missing | No capacity model or saturation signals are implemented. |
| INV-72-C070 | Missing | No release gate blocks performance regressions. |

## Observability & Explainability

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C071 | Partial | Version is locally exposed, but health/readiness/configuration/dependency/capability status endpoints or reports are absent. |
| INV-72-C072 | Missing | Metrics are named in the contract but no metric emitter/export path is implemented. |
| INV-72-C073 | Missing | No structured logging pipeline with stable identifiers exists. |
| INV-72-C074 | Missing | No trace-context propagation exists. |
| INV-72-C075 | Missing | No high-cardinality diagnostic privacy/redaction policy is implemented. |
| INV-72-C076 | Partial | Refusal reasons are returned for many decisions, but successful-selection rationale is not structured or complete. |
| INV-72-C077 | Missing | No operator explain view links decisions to inputs, policy, topology, and constraints. |
| INV-72-C078 | Missing | No correlation with release lineage or a live infrastructure graph exists. |
| INV-72-C079 | Missing | No telemetry retention, sampling, privacy, or export policy exists. |
| INV-72-C080 | Missing | No dashboards or alert rules exist. |

## Testing & Certification

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C082 | Partial | The public matcher is unit-tested, but there are no versioned schema contract tests for all declared interfaces and the `pk_core` contract path is unavailable locally. |
| INV-72-C083 | Missing | No integration tests cover every supported adjacent layer/execution tier. |
| INV-72-C084 | Missing | No CPU/runtime/hypervisor/provider/protocol compatibility matrix or test matrix exists. |
| INV-72-C085 | Missing | No fuzz/property-based untrusted-input harness exists. |
| INV-72-C086 | Missing | No concurrency/race-condition test suite exists. |
| INV-72-C087 | Partial | Isolation and hostile-value cases are tested, but tests are not derived from a complete threat model and do not cover the required attack classes. |
| INV-72-C088 | Missing | No benchmark, soak, burst, or fleet-scale test suite exists. |
| INV-72-C089 | Missing | No disaster/partition/reconnect/degraded-control-plane tests exist. |
| INV-72-C090 | Unverified external | The README points to `pk_core` machine-readable evidence/gating, but neither the framework nor generated acceptance evidence is included, so this cannot be verified. |

## Operations, Release & Governance

| ID | Status | Missing / incomplete component |
|---|---|---|
| INV-72-C091 | Partial | Three SLO/error-budget declarations exist, but support commitments and measured enforcement are absent. |
| INV-72-C092 | Partial | README describes rollout/rollback intent, but there are no executable canary/staged-rollout/rollback/emergency-disable procedures. |
| INV-72-C093 | Missing | No supported-version compatibility matrix exists for `pk_core` or adjacent dependencies. |
| INV-72-C094 | Missing | No patching, vulnerability-response, or end-of-life SLA/policy exists. |
| INV-72-C095 | Missing | No backup/restore/migration/reconstruction procedure exists for ownership/state; durability ownership is not defined. |
| INV-72-C096 | Partial | README contains day-0/day-1/day-2 intent, but not complete operator runbooks with prerequisites, checks, failure paths, and recovery commands. |
| INV-72-C097 | Missing | No incident severity, paging, escalation, containment, or recovery runbook exists. |
| INV-72-C098 | Missing | No recurring access/policy/dependency/configuration/architecture review schedule or evidence exists. |
| INV-72-C099 | Missing | No exception/waiver/technical-debt/deprecation register with owners and expiries exists. |
| INV-72-C100 | Unverified external | A `pk_core gate` command is documented, but the external framework and production acceptance artifacts are absent; a formal repository-local exit gate is not implemented. |

## Locally implemented checklist evidence

Concrete local evidence was found for C001–C008 (scope/ownership/dependencies/source-of-truth/assumptions/boundaries/mandatory-vs-optional/non-goals) and C081 (deterministic matcher unit tests). All other checklist items are listed above as partial, missing, or externally unverified.
