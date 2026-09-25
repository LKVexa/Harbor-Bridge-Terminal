# INV-67 v4.2.0 — Missing Component Implementation Checklist

**Repository:** `inv67_kubernetes_integration_mechanism`  
**Baseline:** v4.2.0 hardened reference translator  
**Source audit:** `inv67_v4.2.0_AUDIT_REPORT.md`  
**Scope:** all 68 missing/incomplete production components identified by the post-hardening audit  
**Purpose:** implementation-ready remediation plan and production-readiness evidence checklist

> This checklist does not redefine the current translator as a complete Kubernetes control plane. It specifies the engineering work required to evolve the v4.2.0 Pod-subset translation boundary into a production-grade Kubernetes integration mechanism and to prove that implementation with reproducible evidence.

## Completion standard

- [ ] A checkbox is complete only when the artifact or behavior exists in the repository/deployed test environment **and** is covered by reproducible evidence.
- [ ] `P0` items are release-blocking foundations/security/correctness controls; `P1` items are required for production completeness; `P2` items may follow only if an approved release policy permits and a time-bounded waiver exists.
- [ ] Tests must assert externally observable behavior and failure semantics, not merely code coverage.
- [ ] Security-sensitive uncertainty must fail closed unless an explicitly designed, approved, observable degraded mode exists.
- [ ] Every component must be linked into the requirements traceability matrix and the final machine-readable production acceptance bundle.
- [ ] No checklist item may be marked complete solely because documentation claims the behavior; code/config/test/operational evidence must support the claim.

## Suggested target repository layout

```text
inv67_kubernetes_integration_mechanism/
  pyproject.toml
  src/inv67/                 # translator + controller/runtime adapters
  schemas/                   # wire/status/config/evidence schemas
  api/crds/                  # Kubernetes CRDs and conversion artifacts
  deploy/base/               # ServiceAccount/RBAC/Deployment/NetworkPolicy/PDB
  deploy/overlays/           # environment/site overlays
  docs/architecture/         # ADRs, state machine, threat model, compatibility
  docs/runbooks/             # day-0/day-1/day-2 and incident procedures
  tests/unit/
  tests/contract/
  tests/integration/
  tests/security/
  tests/fuzz/
  tests/performance/
  tests/fault/
  evidence/                  # generated only; immutable release results
  .github/workflows/ or CI equivalent
```

Paths are recommendations; equivalent repository conventions are acceptable if ownership and evidence remain unambiguous.

# Phase A — Architecture, ownership, and requirements

## 01. Accountable owner and escalation model

**Audit mapping:** C009  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create `docs/OWNERSHIP.md` naming primary team/role, secondary owner, support channel, and escalation contacts/roles without relying on tribal knowledge.
- [ ] Define responsibility boundaries for translator maintenance, Kubernetes controller ownership, downstream scheduler/runtime ownership, security approval, and release authority.
- [ ] Define operational coverage expectations, incident acknowledgement targets, handoff rules, and the condition under which escalation moves to platform/security/runtime teams.
- [ ] Define ownership-transfer procedure including open-risk review, credential/RBAC transfer, pending incidents, exception ledger, and acceptance by the receiving owner.
- [ ] Add repository CODEOWNERS or equivalent review enforcement for security-sensitive files, schemas, CRDs, RBAC, release workflow, and controller code.
- [ ] Define who may approve compatibility changes, schema changes, security exceptions, rollback, and emergency disablement.
- [ ] Record current owner and escalation metadata in machine-readable release evidence so deployed artifacts can be traced back to an accountable team.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the accountable owner and escalation model artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Accountable owner and escalation model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Accountable owner and escalation model is implemented, negative-path tested, observable/operable, linked to C009, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 02. Approved architecture decision record

**Audit mapping:** C010, C031  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Author an ADR selecting the Kubernetes integration pattern: controller/operator, webhook, sidecar, gateway, or hybrid; explicitly justify rejected alternatives.
- [ ] Decide whether INV-67 owns a dedicated CRD, consumes native Pod resources, or combines both; define object ownership and status ownership precisely.
- [ ] Define controller topology: namespace-scoped vs cluster-scoped, single vs multi-replica, shard strategy, leader election, and tenancy isolation.
- [ ] Define the Host-Wasm lifecycle mapping from Kubernetes desired state through translated placement request, scheduler/resource-packing decision, runtime launch, status feedback, termination, and deletion.
- [ ] Define deletion semantics, finalizers, graceful shutdown, force-delete behavior, orphan cleanup, and downstream cancellation.
- [ ] Define data-flow and trust-boundary diagrams showing API server, INV-67, PLN-02, SCH-01, INV-68, GAP-15, runtime, secret store, telemetry, and evidence sinks.
- [ ] Specify state ownership for every field and record so multiple controllers cannot race or overwrite each other.
- [ ] Define upgrade strategy for controller, schemas/CRDs, downstream protocols, and in-flight resources, including rollback under mixed versions.
- [ ] Obtain documented review/approval from platform architecture, security, operations/SRE, and downstream owners.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the approved architecture decision record artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Approved architecture decision record** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Approved architecture decision record is implemented, negative-path tested, observable/operable, linked to C010, C031, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 03. Normative SHALL-level requirements specification

**Audit mapping:** C011-C012  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a normative requirements document using stable IDs such as `INV67-REQ-###` and RFC 2119/8174 terms.
- [ ] Translate the product statement “Host Wasm management inside existing Kubernetes estates” into externally testable behavior rather than implementation aspirations.
- [ ] Specify exact supported Kubernetes input surface, including object kinds, fields, defaulting assumptions, validation rules, resource quantity semantics, and unsupported-field refusal behavior.
- [ ] Specify translation fidelity requirements for metadata, identity, images, resources, placement constraints, lifecycle, cancellation, and status.
- [ ] Specify security requirements for authentication, authorization, tenancy, secret handling, artifact trust, transport security, and auditability.
- [ ] Specify resilience requirements for API outage, downstream outage, retry, replay, duplicate events, leader loss, restart, partition, and reconnect.
- [ ] Specify performance/SLO requirements with measurable thresholds and measurement points.
- [ ] Specify observability and operator requirements including conditions, metrics, logs, traces, diagnostics, and explainability.
- [ ] Link each SHALL to one or more automated tests and evidence records; untestable requirements must be rewritten or explicitly justified.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the normative shall-level requirements specification artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Normative SHALL-level requirements specification** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Normative SHALL-level requirements specification is implemented, negative-path tested, observable/operable, linked to C011-C012, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 04. Failure and lifecycle semantics specification

**Audit mapping:** C014-C015  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define canonical lifecycle states for requested, validating, admitted, queued, placed, starting, running, succeeded, failed, cancelled, deleting, degraded, blocked, and unknown where applicable.
- [ ] Define legal state transitions and reject or reconcile illegal transitions deterministically.
- [ ] Separate desired state, observed Kubernetes state, downstream runtime state, and projected status; define which is authoritative during disagreement.
- [ ] Define retryable vs terminal error taxonomy with stable machine-readable codes and human-readable reason/detail fields.
- [ ] Specify generation/attempt identifiers so retries and stale status cannot be mistaken for the current execution.
- [ ] Define partial-success semantics for multi-container or multi-unit workloads and how aggregate Kubernetes status is derived.
- [ ] Define deletion/finalization ordering, downstream cancellation, timeout, leak detection, and orphan remediation.
- [ ] Define behavior for unknown downstream state and stale observation, including when status becomes `Unknown` or `Degraded`.
- [ ] Define who owns retry decisions at each boundary to prevent nested retry storms.
- [ ] Provide a state-transition table and model-based tests covering every legal and illegal transition.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the failure and lifecycle semantics specification artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Failure and lifecycle semantics specification** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Failure and lifecycle semantics specification is implemented, negative-path tested, observable/operable, linked to C014-C015, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 05. Compatibility/versioning policy

**Audit mapping:** C016, C027, C093  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Publish a compatibility matrix for Kubernetes minor versions, Python/runtime version, pk_core version, SCH-01, INV-68, PLN-02, GAP-15, and downstream protocol/schema versions.
- [ ] Define semantic-versioning rules for Python APIs, JSON schemas, CRDs, configuration schemas, and wire contracts.
- [ ] Define supported version-skew windows between controller replicas, CRD storage/served versions, and downstream services.
- [ ] Define deprecation notice period, feature removal process, migration tooling expectations, and EOL policy.
- [ ] Specify CRD conversion/storage-version migration strategy if more than one CRD version can exist.
- [ ] Define forward/backward compatibility behavior for unknown enum values, optional fields, and feature-negotiation bits.
- [ ] Define startup compatibility checks and fail/operate-degraded rules when peers are outside the supported matrix.
- [ ] Add automated compatibility fixtures and matrix CI jobs for every supported combination.
- [ ] Require release notes to state compatibility additions/removals and migration actions.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the compatibility/versioning policy artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Compatibility/versioning policy** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Compatibility/versioning policy is implemented, negative-path tested, observable/operable, linked to C016, C027, C093, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 06. Capacity, quota, and fairness model

**Audit mapping:** C017, C028, C067, C069  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define workload dimensions used for admission and capacity: objects, containers/units, CPU/memory requested, queue depth, API calls, downstream RPCs, tenants, namespaces, and sites.
- [ ] Specify hard ceilings and soft thresholds globally and per tenant/namespace/workload, including defaults and maximum configurable values.
- [ ] Define fairness algorithm (for example weighted fair queueing, deficit round robin, or bounded per-tenant concurrency) and starvation-prevention behavior.
- [ ] Define API client QPS/burst budgets and reconcile fan-out bounds to protect the Kubernetes API server.
- [ ] Define queue capacity, enqueue coalescing rules, duplicate suppression, backpressure, and overload rejection semantics.
- [ ] Define how downstream scheduler/resource-packing saturation feeds admission or throttling decisions.
- [ ] Specify quota accounting atomicity and release rules across retries, failures, cancellation, and deletion.
- [ ] Expose capacity/saturation signals and per-tenant utilization without unsafe high-cardinality metrics.
- [ ] Create load tests demonstrating fairness, bounded memory, and stable recovery under noisy-neighbor scenarios.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the capacity, quota, and fairness model artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Capacity, quota, and fairness model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Capacity, quota, and fairness model is implemented, negative-path tested, observable/operable, linked to C017, C028, C067, C069, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 07. Disconnected/intermittent-control-plane behavior

**Audit mapping:** C018, C048, C056, C089  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define operation when Kubernetes API access is lost: what continues, what freezes, what is rejected, and what state is considered safe.
- [ ] Define operation when downstream scheduler/runtime/identity/compatibility services are unreachable independently.
- [ ] Define stale-cache thresholds and the point at which cached data may no longer authorize mutation or launch.
- [ ] Define write buffering policy, if any; if buffering is prohibited, make the refusal explicit and observable.
- [ ] Define reconnect algorithm: relist, resourceVersion reset, conflict detection, replay/coalescing, and reconciliation priority.
- [ ] Define conflict resolution when Kubernetes desired state changed while INV-67 or a downstream peer was disconnected.
- [ ] Define safety precedence for deletion/revocation vs launch when control-plane information is stale.
- [ ] Persist enough generation/idempotency information to avoid duplicate launch/cancel operations after reconnect.
- [ ] Test prolonged outage, flapping connectivity, watch expiration, stale cache, and reconnect storms.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the disconnected/intermittent-control-plane behavior artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Disconnected/intermittent-control-plane behavior** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Disconnected/intermittent-control-plane behavior is implemented, negative-path tested, observable/operable, linked to C018, C048, C056, C089, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 08. Constraint-precedence policy

**Audit mapping:** C019  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Enumerate all constraint classes: security, authorization, compatibility, residency, tenant policy, resource limits, placement, availability/SLO, cost, affinity, user preference, and operational override.
- [ ] Define a deterministic precedence order and document which constraints are hard vs soft.
- [ ] Make security, authorization, artifact trust, and regulatory constraints non-overridable except through a separately governed exception mechanism.
- [ ] Define conflict codes that name the constraints in conflict and identify the deciding rule.
- [ ] Ensure equivalent constraint sets produce deterministic decisions independent of map/dictionary iteration order.
- [ ] Version the policy and include the policy version/digest in decision records and explain output.
- [ ] Add table-driven tests for pairwise and multi-way conflicts, including ties and missing information.
- [ ] Require changes to precedence to pass architecture/security review and compatibility assessment.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the constraint-precedence policy artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Constraint-precedence policy** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Constraint-precedence policy is implemented, negative-path tested, observable/operable, linked to C019, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 09. Requirements traceability matrix

**Audit mapping:** C020  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a machine-readable matrix (JSON/YAML/CSV) linking each checklist ID and normative requirement ID to design, implementation, tests, evidence, owner, and release gate.
- [ ] Require every `present` claim to reference immutable evidence paths/digests rather than prose assertions.
- [ ] Represent `partial`, `waived`, `not-applicable`, and `blocked` states explicitly with rationale and expiry/owner where relevant.
- [ ] Validate in CI that every normative requirement has at least one verification method and every release gate has evidence.
- [ ] Link source/test locations by stable symbol or path and avoid brittle line-number-only references.
- [ ] Include last-verified release, tool versions, and evidence hashes.
- [ ] Generate a human-readable coverage report from the machine-readable matrix.
- [ ] Fail release if mandatory requirements are missing evidence or have expired waivers.
- [ ] Record the component boundary, source of truth, authoritative inputs/outputs, invariants, and non-goals in a version-controlled design document.
- [ ] Define stable identifiers and version fields for every persistent or externally visible record introduced by this component.
- [ ] Document failure ownership: which layer detects, classifies, retries, escalates, and ultimately resolves each failure class.
- [ ] Document upgrade, downgrade, rollback, and mixed-version behavior before implementation is accepted.
- [ ] Define explicit security assumptions and trust boundaries; do not inherit implicit trust from namespace, network location, or process locality.

### Verification and negative-path checklist

- [ ] Review the requirements traceability matrix artifact against the normative INV-67 requirements and confirm there are no orphan requirements or contradictory ownership statements.
- [ ] Exercise at least one tabletop scenario for upgrade, rollback, dependency outage, and security incident to prove the specification is operationally actionable.
- [ ] Validate all diagrams/tables/version matrices referenced by the design are kept under version control and reviewed when interfaces change.
- [ ] Record reviewer roles, approval date, design version/digest, unresolved risks, and required follow-up actions.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Requirements traceability matrix** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Requirements traceability matrix is implemented, negative-path tested, observable/operable, linked to C020, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase B — Kubernetes-native integration plane

## 10. Actual CRD/API artifacts

**Audit mapping:** C010, C022, C031  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Decide and document the Kubernetes API surface: native Pod watch only, dedicated CRD(s), or both; implement only the approved architecture.
- [ ] If using CRDs, create `apiextensions.k8s.io/v1` manifests with structural OpenAPI v3 schema, served/storage versions, scope, names, short names, and categories.
- [ ] Define `spec` vs `status` separation; enable the status subresource and prohibit user mutation of controller-owned status fields.
- [ ] Add defaults and CEL validations for cross-field invariants that can be enforced safely at admission time.
- [ ] Define printer columns for operator-critical state such as phase, reason, runtime ID, generation, age, and site.
- [ ] Define conversion strategy/webhook if multiple API versions are served; provide round-trip tests and storage migration plan.
- [ ] Define finalizers and lifecycle fields with explicit ownership and deletion semantics.
- [ ] Generate schema fixtures and validate manifests with Kubernetes schema tooling in CI.
- [ ] Install CRDs in an ephemeral cluster and verify create/update/patch/status/finalize behavior against every supported Kubernetes version.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Actual CRD/API artifacts** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Actual CRD/API artifacts is implemented, negative-path tested, observable/operable, linked to C010, C022, C031, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 11. Kubernetes controller/reconciler

**Audit mapping:** C014-C015, C025, C037, C053, C057-C058  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Implement a controller entrypoint and reconcile loop that converts event notifications into idempotent desired/observed-state convergence.
- [ ] Use keyed work queues and coalesce duplicate events; never execute irreversible side effects directly from watch callbacks.
- [ ] Define the reconciliation key (namespace/name/UID) and verify UID to prevent name-reuse confusion.
- [ ] Read the latest object state at reconcile time and compare generation/resourceVersion before writing.
- [ ] Separate pure translation from side effects so `translator.py` remains deterministic and independently testable.
- [ ] Implement finalizer add/remove and deletion reconciliation with downstream cancellation and leak detection.
- [ ] Implement status/condition patching through a dedicated writer with conflict retries and field ownership.
- [ ] Classify reconciliation results into success, requeue-after, retryable dependency error, terminal validation/refusal, and operator-action-required.
- [ ] Enforce bounded concurrency and per-tenant fairness; expose queue depth, work duration, retries, drops/coalescing, and poison items.
- [ ] Handle process restart and leader handoff without duplicate runtime launches via durable idempotency keys/generation IDs.
- [ ] Provide fake-client unit tests plus envtest/kind integration tests covering create/update/delete, retries, conflict, restart, and finalizers.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Kubernetes controller/reconciler** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Kubernetes controller/reconciler is implemented, negative-path tested, observable/operable, linked to C014-C015, C025, C037, C053, C057-C058, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 12. Kubernetes client and cluster connection layer

**Audit mapping:** C021, C025, C028, C040  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Implement in-cluster service-account configuration and explicit kubeconfig mode for development/test without ambiguous fallback behavior.
- [ ] Configure API QPS/burst, request timeout, dial/TLS timeout, idle connection behavior, and user-agent identifying INV-67 version.
- [ ] Support discovery and feature checks for required APIs/resources before declaring ready.
- [ ] Implement list/watch with resourceVersion semantics, bookmarks where supported, 410 Gone recovery, reconnect backoff, and relist.
- [ ] Propagate cancellation/deadline context through all API operations.
- [ ] Use patch/update strategies that preserve field ownership; include resourceVersion preconditions where needed for correctness.
- [ ] Classify Kubernetes API errors (NotFound, Conflict, Forbidden, TooManyRequests, ServerTimeout, ServiceUnavailable) into stable internal categories.
- [ ] Expose API request latency/error/throttle metrics without leaking bearer tokens or sensitive object data.
- [ ] Test certificate rotation, API restart, DNS failure, throttling, network partition, and kubeconfig/in-cluster authentication failure.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Kubernetes client and cluster connection layer** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Kubernetes client and cluster connection layer is implemented, negative-path tested, observable/operable, linked to C021, C025, C028, C040, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 13. Status writer and condition model

**Audit mapping:** C015, C021, C026, C071, C076  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define a condition taxonomy with stable `type`, `status`, `reason`, `message`, `observedGeneration`, and transition time semantics.
- [ ] Define phase projection separately from Conditions so a single coarse Pod phase does not erase actionable state.
- [ ] Implement conflict-safe status patching and retry only on safe conflict/throttle errors.
- [ ] Track `observedGeneration` and refuse to mark current readiness/success using status derived from an older generation.
- [ ] Define ownership of each status field and ensure INV-67 does not overwrite kubelet/peer-controller status it does not own.
- [ ] Rate-limit status updates and suppress no-op writes to avoid API churn.
- [ ] Represent unknown/stale downstream state explicitly with last-successful observation timestamp and reason.
- [ ] Attach runtime/scheduler correlation identifiers without exposing secrets.
- [ ] Test concurrent status writers, stale resourceVersion, rapid state flapping, controller restart, deletion, and unknown runtime states.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Status writer and condition model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Status writer and condition model is implemented, negative-path tested, observable/operable, linked to C015, C021, C026, C071, C076, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 14. Downstream scheduler/runtime adapter

**Audit mapping:** C003, C021, C025, C030, C083  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define versioned request/response schemas for SCH-01, INV-68, and runtime interactions, including idempotency key, tenant, workload UID, generation, resource requests/limits, and metadata.
- [ ] Select transport and security profile (for example mTLS gRPC/HTTP) and specify timeout/cancellation semantics.
- [ ] Implement idempotent `place/start/cancel/query` operations or equivalent, with stable operation IDs and replay-safe semantics.
- [ ] Do not multiply retries across layers; specify retry ownership and budgets between INV-67 and downstream services.
- [ ] Implement backpressure and circuit breaking when downstream capacity is exhausted or the service is unhealthy.
- [ ] Map downstream error codes into INV-67 lifecycle/condition reasons without collapsing distinct causes.
- [ ] Validate peer schema/protocol version and compatibility before sending mutable/irreversible operations.
- [ ] Propagate trace/correlation context and attach Kubernetes UID/generation for end-to-end diagnosis.
- [ ] Add contract tests using protocol fixtures and integration tests against real/test scheduler/runtime endpoints.
- [ ] Prove cancellation/deletion reaches the runtime and does not leak workloads after controller restart or network partition.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Downstream scheduler/runtime adapter** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Downstream scheduler/runtime adapter is implemented, negative-path tested, observable/operable, linked to C003, C021, C025, C030, C083, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 15. Application identity mapping implementation

**Audit mapping:** C003, C006, C023-C024, C046  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define the authoritative application identity and the exact mapping from Kubernetes namespace/service-account/labels/annotations/ownerRefs to PLN-02 identity.
- [ ] Do not accept user-controlled labels/annotations as authoritative identity unless signed or independently validated.
- [ ] Implement namespace/tenant binding lookup with cache TTL and revocation behavior.
- [ ] Validate ownership/tenant before translating or sending downstream placement requests.
- [ ] Define lifecycle linkage for application deletion, transfer, rename, and namespace move/recreation.
- [ ] Use immutable Kubernetes UID and authoritative PLN-02 ID in correlation and authorization decisions.
- [ ] Return machine-readable refusal when identity is ambiguous, missing, stale, unauthorized, or conflicts with policy.
- [ ] Audit identity-binding changes and cache hits/misses without logging credentials/tokens.
- [ ] Test cross-tenant spoofing, namespace recreation, stale identity cache, revoked app, and conflicting mappings.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Application identity mapping implementation** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Application identity mapping implementation is implemented, negative-path tested, observable/operable, linked to C003, C006, C023-C024, C046, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 16. Resource and feature compatibility/certification adapter

**Audit mapping:** C027, C084  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define a machine-readable capability model for supported Kubernetes/runtime features and resource semantics.
- [ ] Integrate GAP-15 lookup/negotiation before admitting features whose support depends on runtime, architecture, site, or version.
- [ ] Use explicit capability/version identifiers rather than free-form strings for policy decisions.
- [ ] Reject unsupported combinations with precise field/capability reason before creating downstream side effects.
- [ ] Cache certification results only with bounded TTL/version keys and invalidate on compatibility-policy changes.
- [ ] Record the certification/capability version used for each placement decision so results are reproducible.
- [ ] Define degraded behavior when GAP-15 is unavailable; security/safety-relevant uncertainty must fail closed.
- [ ] Create compatibility fixtures spanning supported/unsupported Kubernetes fields, runtimes, architectures, and versions.
- [ ] Test stale capability cache, capability downgrade, peer upgrade, and mixed-version site behavior.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Resource and feature compatibility/certification adapter** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Resource and feature compatibility/certification adapter is implemented, negative-path tested, observable/operable, linked to C027, C084, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 17. Deployment manifests/packaging

**Audit mapping:** C032-C040, C042-C043, C092  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a Deployment/StatefulSet or operator bundle matching the approved controller topology and HA model.
- [ ] Create a dedicated ServiceAccount and least-privilege Roles/ClusterRoles restricted to exact resources, verbs, namespaces, and status/finalizer needs.
- [ ] Bind RBAC narrowly; avoid wildcard resources, verbs, API groups, and broad secret read access.
- [ ] Create ConfigMap/Secret references with documented keys, ownership, rotation, and restart/reload behavior.
- [ ] Define NetworkPolicies for Kubernetes API, downstream services, telemetry, and approved DNS/identity endpoints.
- [ ] Set securityContext to non-root, read-only root filesystem, dropped capabilities, seccomp profile, no privilege escalation, and minimal writable volumes.
- [ ] Set requests/limits, probes, terminationGracePeriod, topology spread/anti-affinity, priority class, PDB, and replica count consistent with SLOs.
- [ ] Provide Helm and/or Kustomize overlays for supported environments without duplicating unvalidated configuration paths.
- [ ] Pin container image by digest for release manifests and include version/config annotations for evidence.
- [ ] Test install/upgrade/rollback/uninstall in a clean cluster and verify that CRDs/finalizers do not strand resources.
- [ ] Use Kubernetes API machinery with context/deadline propagation, resourceVersion-aware concurrency, and idempotent reconciliation semantics.
- [ ] Treat watch streams as lossy notifications: recover from compaction/410 Gone, reconnect with bounded backoff, and re-list to reconstruct observed state.
- [ ] Use server-side validation/defaulting where appropriate, but never rely on admission behavior as the only validation layer for security-sensitive invariants.
- [ ] Ensure writes are patch/field-manager scoped so INV-67 does not overwrite fields owned by users or peer controllers.
- [ ] Exercise behavior against supported Kubernetes minor versions rather than only against mocks.

### Verification and negative-path checklist

- [ ] Run unit tests with deterministic fake clients for success, malformed input, NotFound, Conflict, Forbidden, throttling, timeout, cancellation, and duplicate delivery.
- [ ] Run integration tests against a real ephemeral Kubernetes API server with the exact RBAC/manifests intended for deployment.
- [ ] Verify create/update/delete/restart/leader-handoff behavior and ensure all external mutations are idempotent under replay.
- [ ] Verify no unknown Kubernetes semantics are silently dropped before a downstream side effect is created.
- [ ] Capture Kubernetes version, manifest/CRD digest, test logs, and resulting object/status snapshots as evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Deployment manifests/packaging** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Deployment manifests/packaging is implemented, negative-path tested, observable/operable, linked to C032-C040, C042-C043, C092, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase C — Configuration and change safety

## 18. Declarative runtime configuration schema

**Audit mapping:** C032-C035  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a versioned schema for API endpoints, peer endpoints, timeouts, retries, queues, feature gates, tenant/site mappings, limits, telemetry, and emergency controls.
- [ ] Assign type, units, bounds, default, mutability, secrecy classification, and restart/reload requirement for every key.
- [ ] Validate configuration before process readiness and before dynamic activation; reject unknown keys unless explicitly allowed.
- [ ] Define deterministic precedence among compiled defaults, configuration files, environment, flags, and dynamic configuration.
- [ ] Keep security-sensitive defaults fail-closed and production-safe; do not rely on operators remembering to harden development defaults.
- [ ] Expose only non-secret effective configuration with source provenance for diagnostics.
- [ ] Version schema migrations and supply conversion/validation tooling for old supported configuration versions.
- [ ] Add positive/negative fixtures and property tests for boundary values, malformed units, duplicate mappings, and conflicting settings.
- [ ] Define a versioned configuration schema with deterministic precedence among defaults, files, environment variables, flags, and dynamic control-plane overrides.
- [ ] Reject unknown or invalid configuration keys unless an explicit forward-compatibility policy says otherwise.
- [ ] Emit a non-secret canonical configuration digest and active schema version for diagnostics and evidence.
- [ ] Make configuration activation atomic and observable; partially applied configuration must not be externally visible.
- [ ] Redact secret values and sensitive identifiers from errors, logs, traces, crash dumps, and evidence bundles.

### Verification and negative-path checklist

- [ ] Test valid, invalid, missing, unknown, boundary, conflicting, stale, and rolled-back configuration.
- [ ] Inject process crash and replica skew during activation and verify atomicity/last-known-good behavior.
- [ ] Verify secret sentinels never appear in configuration diagnostics or evidence.
- [ ] Record schema digest, active config digest, activation history, and rollback test result in evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Declarative runtime configuration schema** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Declarative runtime configuration schema is implemented, negative-path tested, observable/operable, linked to C032-C035, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 19. Configuration provenance and activation record

**Audit mapping:** C036, C045, C049  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Assign each configuration bundle an immutable content digest, schema version, author/source, creation timestamp, and optional approval/ticket reference.
- [ ] Record activation attempt, validator result, prior digest, new digest, actor, target site/tenant scope, and outcome.
- [ ] Store activation history in an append-only or tamper-evident evidence sink with retention policy.
- [ ] Include active configuration digest in health endpoint, logs, traces, conditions, and release evidence.
- [ ] Record exact external references used by configuration (secret IDs, policy versions, compatibility versions) without recording secret values.
- [ ] Make provenance available during incident reconstruction even if the originating configuration service is unavailable.
- [ ] Test that rejected/partial activations cannot be mistaken for active configuration and that rollback produces a new auditable activation record.
- [ ] Define a versioned configuration schema with deterministic precedence among defaults, files, environment variables, flags, and dynamic control-plane overrides.
- [ ] Reject unknown or invalid configuration keys unless an explicit forward-compatibility policy says otherwise.
- [ ] Emit a non-secret canonical configuration digest and active schema version for diagnostics and evidence.
- [ ] Make configuration activation atomic and observable; partially applied configuration must not be externally visible.
- [ ] Redact secret values and sensitive identifiers from errors, logs, traces, crash dumps, and evidence bundles.

### Verification and negative-path checklist

- [ ] Test valid, invalid, missing, unknown, boundary, conflicting, stale, and rolled-back configuration.
- [ ] Inject process crash and replica skew during activation and verify atomicity/last-known-good behavior.
- [ ] Verify secret sentinels never appear in configuration diagnostics or evidence.
- [ ] Record schema digest, active config digest, activation history, and rollback test result in evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Configuration provenance and activation record** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Configuration provenance and activation record is implemented, negative-path tested, observable/operable, linked to C036, C045, C049, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 20. Atomic configuration rollout and rollback

**Audit mapping:** C037-C038, C092  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Implement validate→stage→activate as an atomic configuration transaction; all components must observe either old or new config, not an arbitrary mixture.
- [ ] Define which keys are dynamically reloadable and which require controlled restart; reject unsupported live mutation.
- [ ] Maintain a last-known-good snapshot and activation metadata locally or in a resilient control store.
- [ ] Define canary/staged rollout semantics across replicas/sites and success criteria before broad promotion.
- [ ] Automatically rollback on configured health/SLO/security guardrail violations when safe, otherwise freeze and require operator action.
- [ ] Provide authenticated operator command/API for scoped rollback to a known digest.
- [ ] Ensure rollback of config does not roll back durable workload generation/state incorrectly.
- [ ] Test invalid config, replica skew, crash during activation, control-store outage, automatic rollback, manual rollback, and rollback-of-rollback.
- [ ] Define a versioned configuration schema with deterministic precedence among defaults, files, environment variables, flags, and dynamic control-plane overrides.
- [ ] Reject unknown or invalid configuration keys unless an explicit forward-compatibility policy says otherwise.
- [ ] Emit a non-secret canonical configuration digest and active schema version for diagnostics and evidence.
- [ ] Make configuration activation atomic and observable; partially applied configuration must not be externally visible.
- [ ] Redact secret values and sensitive identifiers from errors, logs, traces, crash dumps, and evidence bundles.

### Verification and negative-path checklist

- [ ] Test valid, invalid, missing, unknown, boundary, conflicting, stale, and rolled-back configuration.
- [ ] Inject process crash and replica skew during activation and verify atomicity/last-known-good behavior.
- [ ] Verify secret sentinels never appear in configuration diagnostics or evidence.
- [ ] Record schema digest, active config digest, activation history, and rollback test result in evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Atomic configuration rollout and rollback** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Atomic configuration rollout and rollback is implemented, negative-path tested, observable/operable, linked to C037-C038, C092, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 21. Secret-handling integration

**Audit mapping:** C039, C047, C075  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Represent secrets by references, not inline cleartext configuration, wherever the platform provides a secret manager.
- [ ] Define supported secret sources and retrieval identity; grant only per-secret/per-prefix access required by INV-67.
- [ ] Implement in-memory handling that minimizes lifetime/copies and never serializes secret material into status, exceptions, telemetry, or evidence.
- [ ] Define certificate/token rotation and refresh behavior without full outage where possible.
- [ ] Redact known secret fields plus token-like values from structured diagnostics and crash/error paths.
- [ ] Fail safely when secret retrieval, decryption, or refresh fails; do not silently continue with expired/revoked credentials.
- [ ] Audit secret reference/access events at metadata level without logging secret values.
- [ ] Add automated tests that inject sentinel secrets and assert they never appear in logs, traces, status, refusal output, or support bundles.
- [ ] Define a versioned configuration schema with deterministic precedence among defaults, files, environment variables, flags, and dynamic control-plane overrides.
- [ ] Reject unknown or invalid configuration keys unless an explicit forward-compatibility policy says otherwise.
- [ ] Emit a non-secret canonical configuration digest and active schema version for diagnostics and evidence.
- [ ] Make configuration activation atomic and observable; partially applied configuration must not be externally visible.
- [ ] Redact secret values and sensitive identifiers from errors, logs, traces, crash dumps, and evidence bundles.

### Verification and negative-path checklist

- [ ] Test valid, invalid, missing, unknown, boundary, conflicting, stale, and rolled-back configuration.
- [ ] Inject process crash and replica skew during activation and verify atomicity/last-known-good behavior.
- [ ] Verify secret sentinels never appear in configuration diagnostics or evidence.
- [ ] Record schema digest, active config digest, activation history, and rollback test result in evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Secret-handling integration** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Secret-handling integration is implemented, negative-path tested, observable/operable, linked to C039, C047, C075, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 22. Deterministic bootstrap implementation

**Audit mapping:** C040, C096  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Provide a clean-machine/bootstrap command that installs or verifies exact runtime/tool dependencies without relying on undeclared global state.
- [ ] Create a preflight that validates Kubernetes connectivity, required APIs/CRDs, RBAC, downstream compatibility, configuration schema, secrets, and network reachability.
- [ ] Make bootstrap idempotent and safe to re-run after partial failure.
- [ ] Emit machine-readable preflight results with PASS/FAIL, reason, version, and remediation hint.
- [ ] Define readiness gate so the controller does not accept work before bootstrap prerequisites are satisfied.
- [ ] Pin/verify dependency hashes or trusted package sources as appropriate.
- [ ] Document empty-cluster-to-healthy commands, expected outputs, and rollback/uninstall path.
- [ ] Exercise bootstrap in CI on a disposable environment and preserve logs/evidence as release artifacts.
- [ ] Define a versioned configuration schema with deterministic precedence among defaults, files, environment variables, flags, and dynamic control-plane overrides.
- [ ] Reject unknown or invalid configuration keys unless an explicit forward-compatibility policy says otherwise.
- [ ] Emit a non-secret canonical configuration digest and active schema version for diagnostics and evidence.
- [ ] Make configuration activation atomic and observable; partially applied configuration must not be externally visible.
- [ ] Redact secret values and sensitive identifiers from errors, logs, traces, crash dumps, and evidence bundles.

### Verification and negative-path checklist

- [ ] Test valid, invalid, missing, unknown, boundary, conflicting, stale, and rolled-back configuration.
- [ ] Inject process crash and replica skew during activation and verify atomicity/last-known-good behavior.
- [ ] Verify secret sentinels never appear in configuration diagnostics or evidence.
- [ ] Record schema digest, active config digest, activation history, and rollback test result in evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Deterministic bootstrap implementation** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Deterministic bootstrap implementation is implemented, negative-path tested, observable/operable, linked to C040, C096, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase D — Security, trust, and supply chain

## 23. Full threat model

**Audit mapping:** C041  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create system/data-flow diagrams covering Kubernetes API, admission path, controller, caches, queues, identity plane, scheduler, resource packer, runtime, secret store, telemetry, artifact registry, and evidence store.
- [ ] Enumerate assets: tenant isolation, workload intent, credentials, artifact integrity, policy, resource quotas, status correctness, audit history, and control-plane availability.
- [ ] Enumerate actors and trust levels: tenant user, cluster admin, compromised workload, compromised node, external attacker, compromised peer service, malicious artifact publisher, insider/operator.
- [ ] Perform STRIDE or equivalent analysis at each trust boundary and data flow.
- [ ] Document abuse cases for privilege escalation, host escape intent, cross-tenant spoofing, replay, stale-cache authorization, resource exhaustion, malicious image reference, log injection, schema downgrade, and status spoofing.
- [ ] Map each threat to preventive/detective controls, verification test, telemetry/alert, residual risk, and owner.
- [ ] Track unresolved threats in the exception/risk ledger with expiry and compensating controls.
- [ ] Require security sign-off for material architecture/protocol/RBAC changes and periodic threat-model refresh.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Full threat model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Full threat model is implemented, negative-path tested, observable/operable, linked to C041, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 24. Authentication design and implementation

**Audit mapping:** C023, C044  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Use Kubernetes ServiceAccount projected tokens or workload identity for API authentication; do not embed static cluster credentials in images.
- [ ] Define downstream service identity using mTLS/SPIFFE/OIDC or the platform-approved mechanism and validate issuer, audience, subject, lifetime, and trust roots.
- [ ] Authenticate peers mutually for privileged control operations; transport encryption without peer authentication is insufficient.
- [ ] Bind runtime/scheduler requests to authenticated INV-67 identity and tenant/workload context.
- [ ] Define node/site identity if decisions depend on site or execution location.
- [ ] Implement credential rotation, overlap, revocation, and expiry handling with clear readiness/degraded behavior.
- [ ] Reject unexpected identity, audience, issuer, SAN, or trust-domain values with stable errors and audit events.
- [ ] Test expired/revoked credentials, wrong audience, wrong trust domain, rotated CA, clock skew, and peer impersonation.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Authentication design and implementation** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Authentication design and implementation is implemented, negative-path tested, observable/operable, linked to C023, C044, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 25. Authorization and least-privilege policy

**Audit mapping:** C024, C042-C043, C046  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create an authorization matrix covering every Kubernetes resource/verb and downstream capability required by INV-67.
- [ ] Generate RBAC from the matrix and prove there are no wildcard verbs/resources/API groups unless explicitly reviewed.
- [ ] Scope namespace access according to deployment mode; cluster-scoped read/watch must be justified and tenant filtered before downstream action.
- [ ] Authorize workload operations using authenticated tenant/application identity, not only possession of Kubernetes API access.
- [ ] Implement deny-by-default checks for translate/place/cancel/status/diagnostic/emergency operations.
- [ ] Separate operational admin privileges from workload-control privileges and from release/configuration privileges.
- [ ] Use SubjectAccessReview or platform policy checks where dynamic authorization is required; define caching and revocation semantics.
- [ ] Audit allowed and denied privileged operations with actor, target, policy version, and reason.
- [ ] Test cross-namespace, cross-tenant, service-account impersonation, stale authorization cache, and wildcard regression cases.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Authorization and least-privilege policy** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Authorization and least-privilege policy is implemented, negative-path tested, observable/operable, linked to C024, C042-C043, C046, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 26. Artifact integrity/provenance verification

**Audit mapping:** C045  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Require immutable image digests for production execution or resolve tags to digests before trust decisions.
- [ ] Verify approved signatures/attestations against trusted identities and policy; define behavior for missing, invalid, expired, or revoked trust.
- [ ] Validate SBOM/provenance attestations and builder/source constraints required by platform policy.
- [ ] Define trusted registries and namespace/repository allow/deny rules.
- [ ] Record verified digest, signer/issuer, provenance policy version, and verification result in decision/audit evidence.
- [ ] Cache verification only by immutable digest and trust-policy version; invalidate on policy/trust-root changes.
- [ ] Prevent TOCTOU by ensuring the exact verified digest is the digest sent to the runtime.
- [ ] Test tag mutation, digest mismatch, forged signature, untrusted issuer, revoked signer, stale cache, registry outage, and policy downgrade.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Artifact integrity/provenance verification** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Artifact integrity/provenance verification is implemented, negative-path tested, observable/operable, linked to C045, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 27. Encryption/key-management integration

**Audit mapping:** C047-C048  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define TLS requirements and minimum protocol/cipher policy for Kubernetes and all downstream/control/evidence endpoints.
- [ ] Define certificate trust roots, identity verification, rotation, revocation, and emergency trust-root replacement.
- [ ] If INV-67 persists sensitive state, define at-rest encryption boundary and which platform/KMS keys protect which data.
- [ ] Use managed key references rather than embedding key material in repository/configuration.
- [ ] Define KMS/secret-manager unavailability behavior, cache lifetime, and what operations must stop when key assurance is unavailable.
- [ ] Ensure plaintext sensitive material is not emitted to temp files, logs, swap-sensitive dumps, or support bundles.
- [ ] Audit key/credential rotation and verification failures.
- [ ] Test expired certs, revoked trust, wrong SAN/audience, KMS outage, key rotation during traffic, and downgrade attempts.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Encryption/key-management integration** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Encryption/key-management integration is implemented, negative-path tested, observable/operable, linked to C047-C048, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 28. Tamper-evident security audit trail

**Audit mapping:** C049, C073, C079  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define an audit event schema with event ID, timestamp, actor identity, tenant, Kubernetes UID, operation, target, decision/result, reason code, policy/config/version digests, and correlation/trace ID.
- [ ] Emit events for authentication/authorization decisions, config activation, policy/compatibility decision, placement/cancel, emergency controls, identity mapping changes, secret reference changes, and release/admin actions.
- [ ] Send audit records to append-only/WORM or cryptographically chained storage appropriate to the platform.
- [ ] Define ordering/clock semantics and how clock uncertainty is represented.
- [ ] Protect the audit sink with separate credentials and least privilege so the workload-control identity cannot rewrite history.
- [ ] Define backpressure/failure behavior: high-risk operations should not silently proceed if mandatory audit recording is unavailable.
- [ ] Define retention, legal/privacy constraints, access review, export, and incident-preservation procedure.
- [ ] Test tampering, dropped sink connection, duplicate event, replay, clock skew, and correlation completeness.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Tamper-evident security audit trail** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Tamper-evident security audit trail is implemented, negative-path tested, observable/operable, linked to C049, C073, C079, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 29. Adversarial security suite

**Audit mapping:** C050, C087  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Build security fixtures for privilege escalation fields, host namespaces, hostPath/device access, dangerous Linux capabilities, seccomp/AppArmor changes, service-account/token exposure, and unsupported admission-sensitive fields.
- [ ] Fuzz JSON/object shapes for type confusion, deep nesting, oversized strings/maps, duplicate semantic keys, Unicode edge cases, and parser resource exhaustion.
- [ ] Test command/argument/image/annotation/log injection paths if those fields become supported.
- [ ] Test replay/duplicate requests against downstream idempotency and cancellation interfaces.
- [ ] Test identity spoofing, cross-tenant binding, stale policy/identity cache, and confused-deputy scenarios.
- [ ] Test malicious quantities and numeric boundaries including exponential forms, non-finite values, extreme precision, and oversized input.
- [ ] Test telemetry/log injection and secret exfiltration sentinels.
- [ ] Integrate SAST, dependency vulnerability, secret scanning, and container/IaC scanning into CI with pinned policy and triage rules.
- [ ] Preserve minimized regression cases for every discovered security defect.
- [ ] Use deny-by-default policy and least privilege for identities, APIs, filesystem access, network access, and downstream capabilities.
- [ ] Bind authorization decisions to authenticated principal, tenant, namespace, workload, operation, and immutable resource identity where applicable.
- [ ] Define replay, spoofing, confused-deputy, privilege-escalation, injection, resource-exhaustion, and downgrade threats and test mitigations.
- [ ] Make security-relevant state changes produce structured audit events with actor, target, decision, reason, and correlation identifiers.
- [ ] Fail closed on unverifiable identity, artifact integrity, policy state, or key material unless an explicitly approved degraded mode exists.

### Verification and negative-path checklist

- [ ] Create explicit positive and negative authorization/authentication/trust test cases, including cross-tenant and stale-cache scenarios.
- [ ] Run adversarial tests under resource limits so parser/policy abuse cannot exhaust the controller.
- [ ] Verify security failures are machine-readable, auditable, non-secret, and fail closed.
- [ ] Obtain security review for the implemented control and link threat-model mitigations to tests/evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Adversarial security suite** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Adversarial security suite is implemented, negative-path tested, observable/operable, linked to C050, C087, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase E — Resilience and distributed-control behavior

## 30. Health/stall detection and readiness model

**Audit mapping:** C052, C071  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define liveness as “process can make internal progress” and readiness as “safe to accept/reconcile work”; do not conflate them.
- [ ] Track Kubernetes watch freshness, queue age/depth, worker heartbeat/progress, downstream connectivity, identity/compatibility freshness, config validity, and credential expiry.
- [ ] Define per-dependency stale/stall thresholds derived from SLOs and normal watch/reconcile behavior.
- [ ] Expose health state with reason codes and timestamps; distinguish transient degradation from terminal misconfiguration.
- [ ] Remove readiness when safe operation cannot be guaranteed, but avoid restart loops for external dependency outages that a process restart cannot fix.
- [ ] Detect poison items and reconcile loops that repeatedly fail without system-wide progress.
- [ ] Emit alerts for stale watch, queue-age breach, dead worker, persistent dependency failure, and readiness flapping.
- [ ] Test dependency blackholes, hung workers, frozen watch with live TCP, full queue, clock skew, and repeated transient errors.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Health/stall detection and readiness model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Health/stall detection and readiness model is implemented, negative-path tested, observable/operable, linked to C052, C071, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 31. Bounded retry/backoff/jitter implementation

**Audit mapping:** C025, C053  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a retry policy table per Kubernetes operation and downstream RPC specifying retryable codes, maximum attempts/time budget, base/max backoff, and jitter strategy.
- [ ] Use deadlines propagated from the originating reconciliation budget; retries must not outlive deletion/cancellation or stale generation.
- [ ] Honor server-provided Retry-After/throttle hints where safe.
- [ ] Prevent synchronized retry storms across replicas by using full/equal jitter and bounded concurrency.
- [ ] Move poison/terminal items to a visible terminal condition or quarantine path rather than infinite retry.
- [ ] Track retry count and cumulative delay by operation/error class.
- [ ] Ensure nested clients do not each independently multiply retry attempts beyond the end-to-end budget.
- [ ] Test throttling, timeout, connection reset, conflict, invalid input, auth failure, cancellation, and leader handoff during backoff.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Bounded retry/backoff/jitter implementation** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Bounded retry/backoff/jitter implementation is implemented, negative-path tested, observable/operable, linked to C025, C053, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 32. Admission control/load shedding/circuit breaking

**Audit mapping:** C054, C067  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define admission points before expensive translation, downstream RPC, and runtime launch.
- [ ] Bound controller queue length, in-flight reconciles, per-tenant concurrency, and downstream in-flight requests.
- [ ] Use overload rejection with stable reason/retry hints rather than unbounded memory growth.
- [ ] Implement circuit breaker states/thresholds for failing downstream services with half-open recovery probing and hysteresis.
- [ ] Preserve critical operations such as deletion/revocation/status convergence preferentially over new launches during overload.
- [ ] Ensure shedding is fair across tenants and does not permit one namespace to monopolize capacity.
- [ ] Expose saturation, rejected/admitted, breaker state, queue age, and downstream error-rate metrics.
- [ ] Test sudden burst, sustained overload, downstream brownout, one noisy tenant, recovery, and repeated breaker oscillation.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Admission control/load shedding/circuit breaking** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Admission control/load shedding/circuit breaking is implemented, negative-path tested, observable/operable, linked to C054, C067, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 33. Failover/leader election/split-brain protection

**Audit mapping:** C055, C058, C086  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Use Kubernetes Lease-based leader election or an equivalent platform mechanism for singleton side effects when required.
- [ ] Set lease duration/renew/deadline values based on worst-case API latency and failure-detection goals; document tradeoffs.
- [ ] Make reconciliation safe even if more than one replica temporarily acts due to lease ambiguity by using idempotency keys/fencing.
- [ ] Attach controller epoch/fencing token or generation to downstream mutating operations if peer APIs support it.
- [ ] Stop issuing privileged mutations promptly after leadership loss/cancellation.
- [ ] Ensure followers remain warm enough to take over without stale-cache unsafe decisions.
- [ ] Record leader identity/epoch and transitions in metrics/logs/audit.
- [ ] Test abrupt leader crash, network partition from API server, long GC/event-loop stall, clock skew, lease renewal delay, and rapid handoff.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Failover/leader election/split-brain protection** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Failover/leader election/split-brain protection is implemented, negative-path tested, observable/operable, linked to C055, C058, C086, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 34. Crash consistency/restart/replay model

**Audit mapping:** C057  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Identify all side effects that can occur between durable state checkpoints and design idempotency around those crash windows.
- [ ] Use stable operation IDs derived from immutable Kubernetes UID + generation/attempt for downstream mutations.
- [ ] Persist or reconstruct enough state to determine whether place/start/cancel already occurred after restart.
- [ ] Query authoritative downstream state before repeating irreversible operations when outcome is unknown.
- [ ] Treat status writes as projections, not proof that the downstream action did or did not happen.
- [ ] Define replay of queued/relisted resources and coalescing after startup.
- [ ] Handle namespace/name reuse by checking UID and generation.
- [ ] Build crash-injection tests at each side-effect boundary and assert no duplicate execution/leak/lost cancellation.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Crash consistency/restart/replay model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Crash consistency/restart/replay model is implemented, negative-path tested, observable/operable, linked to C057, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 35. Quarantine/freeze/emergency-disable control

**Audit mapping:** C059, C092  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define scoped controls for global, site, tenant, namespace, application, and workload quarantine/freeze where operationally required.
- [ ] Separate “block new launches” from “cancel existing workloads” and make destructive behavior explicit.
- [ ] Require authenticated/authorized operator identity, reason, expiry, and ticket/reference for emergency actions.
- [ ] Persist emergency state in an authoritative control store that survives controller restart and replica failover.
- [ ] Propagate emergency state to admission/reconciliation before downstream side effects.
- [ ] Emit prominent condition/status and tamper-evident audit events for activation, extension, and release.
- [ ] Provide safe re-enable workflow that reconciles current desired state rather than blindly replaying old queued actions.
- [ ] Test activation during outage, leader handoff, stale cache, partial scope, expiry, and control-store unavailability.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Quarantine/freeze/emergency-disable control** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Quarantine/freeze/emergency-disable control is implemented, negative-path tested, observable/operable, linked to C059, C092, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 36. Fault-injection/partition/reconnect test suite

**Audit mapping:** C060, C089  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a deterministic fault harness for Kubernetes API latency/error/drop, watch closure/compaction, DNS failure, packet loss, scheduler/runtime outage, identity/compatibility outage, and telemetry/audit sink outage.
- [ ] Inject process crash and restart before/after every major side effect and status write.
- [ ] Inject leader loss and multi-replica partition scenarios to validate fencing/idempotency.
- [ ] Simulate stale caches and conflicting Kubernetes updates while disconnected.
- [ ] Exercise node/site loss and downstream state unknown scenarios.
- [ ] Assert bounded retry/queue memory, no cross-tenant leakage, no duplicate runtime launches, no lost deletion, and eventual convergence after recovery.
- [ ] Measure recovery time and reconcile storm magnitude after reconnect.
- [ ] Run fault scenarios in CI/nightly certification with stored traces/logs/evidence.
- [ ] Classify failures as retryable, terminal, conflict, throttled, dependency-unavailable, invalid-input, or operator-action-required.
- [ ] Apply bounded retries with exponential backoff and jitter only to operations proven safe to retry; propagate absolute deadlines.
- [ ] Prove idempotency across duplicate delivery, restart, leader handoff, stale cache, and reconnect.
- [ ] Define overload behavior before saturation: bounded queues, admission limits, backpressure, shedding, and recovery hysteresis.
- [ ] Verify state reconstruction after process crash and dependency outage without duplicate side effects or silent data loss.

### Verification and negative-path checklist

- [ ] Use deterministic fault injection to cover outage, partial failure, timeout, cancellation, restart, replay, and recovery.
- [ ] Verify queue/memory/retry work remains bounded during the fault and converges after recovery.
- [ ] Verify no duplicate workload launch, lost cancellation/deletion, cross-tenant action, or stuck finalizer is produced.
- [ ] Measure detection and recovery time and compare them with the declared SLO/operational target.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Fault-injection/partition/reconnect test suite** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Fault-injection/partition/reconnect test suite is implemented, negative-path tested, observable/operable, linked to C060, C089, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase F — Performance and resource efficiency

## 37. Reproducible performance benchmark harness

**Audit mapping:** C061, C063-C064, C068  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create separate microbenchmarks for pure `quantity()`, `translate()`, refusal serialization, and `project_status()`.
- [ ] Create controller benchmarks for event-to-reconcile, list/watch processing, queue throughput, status patching, and downstream adapter calls.
- [ ] Define representative Pod fixtures by container count, metadata size, resource field combinations, and unsupported-field complexity.
- [ ] Measure cold-start and steady-state behavior separately.
- [ ] Capture CPU time, wall time, RSS/peak memory, allocations where practical, network/API request counts, and downstream calls per reconciliation.
- [ ] Run on pinned/recorded hardware or normalized CI runners and record Python/kernel/container/Kubernetes versions.
- [ ] Warm up and sample enough iterations to report p50/p95/p99/max with confidence/variation information.
- [ ] Publish raw results plus summary and exact command line in release evidence.
- [ ] Define the workload model, dataset, concurrency, hardware/runtime environment, warm-up policy, sampling method, and statistical treatment used by benchmarks.
- [ ] Measure latency distribution, throughput, CPU, memory, allocation pressure, storage/network cost where applicable, and saturation point.
- [ ] Store benchmark raw data and summarized baselines as versioned release evidence.
- [ ] Add a regression budget and automated gate with an explicit process for approved baseline changes.
- [ ] Profile before optimizing and preserve correctness/security invariants when introducing caching, batching, parallelism, or zero-copy techniques.

### Verification and negative-path checklist

- [ ] Run on a declared reproducible environment and record exact code/artifact/tool/runtime versions.
- [ ] Report distributions and resource use, not only averages.
- [ ] Compare against the stored baseline and explain/approve any material regression.
- [ ] Ensure benchmark fixtures include worst-case valid and invalid inputs rather than only a tiny happy path.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Reproducible performance benchmark harness** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Reproducible performance benchmark harness is implemented, negative-path tested, observable/operable, linked to C061, C063-C064, C068, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 38. Complete performance SLO envelope

**Audit mapping:** C013, C062  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Retain or revise the p99 <5 ms translation target using a defined fixture and measurement environment.
- [ ] Add p50/p95 and worst-case/bounded pathological-input targets for translator/refusal paths.
- [ ] Define controller end-to-end reconcile latency SLO from observed Kubernetes change to downstream acknowledgement/status projection.
- [ ] Define sustained throughput target in reconciliations/events per second and supported object count.
- [ ] Define startup/readiness and leader-failover recovery targets.
- [ ] Define maximum steady-state and burst queue age/depth, CPU, memory, and API QPS at declared capacity.
- [ ] Define saturation behavior and recovery target after overload/outage.
- [ ] Map each SLO to telemetry source, alert threshold, benchmark/certification test, and error budget.
- [ ] Define the workload model, dataset, concurrency, hardware/runtime environment, warm-up policy, sampling method, and statistical treatment used by benchmarks.
- [ ] Measure latency distribution, throughput, CPU, memory, allocation pressure, storage/network cost where applicable, and saturation point.
- [ ] Store benchmark raw data and summarized baselines as versioned release evidence.
- [ ] Add a regression budget and automated gate with an explicit process for approved baseline changes.
- [ ] Profile before optimizing and preserve correctness/security invariants when introducing caching, batching, parallelism, or zero-copy techniques.

### Verification and negative-path checklist

- [ ] Run on a declared reproducible environment and record exact code/artifact/tool/runtime versions.
- [ ] Report distributions and resource use, not only averages.
- [ ] Compare against the stored baseline and explain/approve any material regression.
- [ ] Ensure benchmark fixtures include worst-case valid and invalid inputs rather than only a tiny happy path.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Complete performance SLO envelope** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Complete performance SLO envelope is implemented, negative-path tested, observable/operable, linked to C013, C062, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 39. Profiling/efficiency analysis

**Audit mapping:** C065-C066  
**Priority:** P2  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Profile translation CPU/allocation hotspots on representative and worst-case fixtures before changing implementation.
- [ ] Measure serialization/deserialization, copying, regex/Decimal parsing, schema validation, queueing, and downstream marshalling costs.
- [ ] For controller paths, quantify Kubernetes API calls and eliminate redundant GET/PATCH cycles without compromising freshness/correctness.
- [ ] Evaluate caching only for immutable/versioned data such as compatibility results; define invalidation keys and memory bounds.
- [ ] Evaluate batching/coalescing for status or downstream operations only if protocol semantics preserve per-workload correctness and cancellation.
- [ ] Document any zero-copy/lazy parsing optimization and its impact on input lifetime and security validation.
- [ ] Compare before/after profile and benchmark data and require statistically meaningful benefit.
- [ ] Retain regression tests proving optimization does not change translation/refusal fidelity.
- [ ] Define the workload model, dataset, concurrency, hardware/runtime environment, warm-up policy, sampling method, and statistical treatment used by benchmarks.
- [ ] Measure latency distribution, throughput, CPU, memory, allocation pressure, storage/network cost where applicable, and saturation point.
- [ ] Store benchmark raw data and summarized baselines as versioned release evidence.
- [ ] Add a regression budget and automated gate with an explicit process for approved baseline changes.
- [ ] Profile before optimizing and preserve correctness/security invariants when introducing caching, batching, parallelism, or zero-copy techniques.

### Verification and negative-path checklist

- [ ] Run on a declared reproducible environment and record exact code/artifact/tool/runtime versions.
- [ ] Report distributions and resource use, not only averages.
- [ ] Compare against the stored baseline and explain/approve any material regression.
- [ ] Ensure benchmark fixtures include worst-case valid and invalid inputs rather than only a tiny happy path.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Profiling/efficiency analysis** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P2 DONE:** Profiling/efficiency analysis is implemented, negative-path tested, observable/operable, linked to C065-C066, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 40. Capacity/saturation model and release regression gate

**Audit mapping:** C069-C070, C088  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Model capacity as a function of watched objects, change rate, reconcile cost, worker count, API QPS, downstream latency, and per-tenant limits.
- [ ] Determine saturation indicators and empirical knee points using load tests.
- [ ] Define fleet-sizing formula and headroom policy for normal, burst, dependency-degraded, and failover modes.
- [ ] Store a versioned benchmark baseline keyed by hardware/runtime environment.
- [ ] Define acceptable regression budgets per metric and noise-handling rules.
- [ ] Make CI/nightly fail when regressions exceed budget unless an approved baseline-change record exists.
- [ ] Include queue/recovery behavior in capacity gates, not only translator microbenchmarks.
- [ ] Verify memory remains bounded under maximum declared queue/object cardinality.
- [ ] Define the workload model, dataset, concurrency, hardware/runtime environment, warm-up policy, sampling method, and statistical treatment used by benchmarks.
- [ ] Measure latency distribution, throughput, CPU, memory, allocation pressure, storage/network cost where applicable, and saturation point.
- [ ] Store benchmark raw data and summarized baselines as versioned release evidence.
- [ ] Add a regression budget and automated gate with an explicit process for approved baseline changes.
- [ ] Profile before optimizing and preserve correctness/security invariants when introducing caching, batching, parallelism, or zero-copy techniques.

### Verification and negative-path checklist

- [ ] Run on a declared reproducible environment and record exact code/artifact/tool/runtime versions.
- [ ] Report distributions and resource use, not only averages.
- [ ] Compare against the stored baseline and explain/approve any material regression.
- [ ] Ensure benchmark fixtures include worst-case valid and invalid inputs rather than only a tiny happy path.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Capacity/saturation model and release regression gate** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Capacity/saturation model and release regression gate is implemented, negative-path tested, observable/operable, linked to C069-C070, C088, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase G — Observability and explainability

## 41. Health/readiness/version/config/capability endpoint

**Audit mapping:** C071  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Expose liveness, readiness, build version/commit, active configuration digest/schema, controller identity/leader state, and supported protocol/schema versions.
- [ ] Expose dependency health/freshness for Kubernetes API, scheduler/runtime, PLN-02 identity, INV-68, GAP-15, secret/KMS, audit sink, and telemetry exporter as applicable.
- [ ] Expose queue depth/oldest age and watch freshness sufficient to distinguish a live-but-stalled controller.
- [ ] Expose active capability/certification policy version without leaking tenant secrets.
- [ ] Use machine-readable JSON and Kubernetes probes; keep endpoint cheap and bounded.
- [ ] Protect detailed diagnostic fields if they reveal topology/security-sensitive data; provide minimal unauthenticated probe paths if required.
- [ ] Document readiness rules and test every dependency-degraded combination.
- [ ] Include endpoint contract in compatibility tests.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Health/readiness/version/config/capability endpoint** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Health/readiness/version/config/capability endpoint is implemented, negative-path tested, observable/operable, linked to C071, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 42. Metrics implementation

**Audit mapping:** C072  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Implement the declared `translated`, `refused`, and `status_syncs` counters with stable names and units.
- [ ] Add reconcile count/duration/result, queue depth/age, retries, Kubernetes API latency/errors/throttles, downstream latency/errors, breaker state, leader state, config reloads, and security-decision counters.
- [ ] Use bounded labels such as result/reason code/operation/peer/site; do not label by arbitrary pod name, UID, image, annotation, or tenant unless an explicitly safe aggregation strategy exists.
- [ ] Use histograms with buckets aligned to SLOs and realistic latency ranges.
- [ ] Expose process/runtime metrics needed for CPU, memory, file descriptor/thread/event-loop saturation diagnosis.
- [ ] Define counter reset and multi-replica aggregation expectations.
- [ ] Add metric contract tests for names, types, labels, cardinality, and important increment paths.
- [ ] Create recording rules for SLO/error-budget and saturation indicators.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Metrics implementation** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Metrics implementation is implemented, negative-path tested, observable/operable, linked to C072, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 43. Structured logging

**Audit mapping:** C073  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define a JSON/event schema with timestamp, severity, event code, component/version, operation, outcome, reason, trace/correlation ID, Kubernetes UID/generation, and bounded tenant/site identifiers.
- [ ] Use stable event codes for machine processing instead of relying on message text.
- [ ] Avoid raw Pod dumps by default; log only necessary bounded metadata and refusal field paths.
- [ ] Sanitize CR/LF/control characters and untrusted strings to prevent log forging/injection.
- [ ] Attach retry attempt/deadline and downstream peer/operation IDs for distributed diagnosis.
- [ ] Define severity rules so expected user refusals are not emitted as software-error noise.
- [ ] Guarantee secrets/tokens/certificates/authorization headers are redacted.
- [ ] Add tests with sentinel secrets and hostile strings; validate logs against the schema.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Structured logging** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Structured logging is implemented, negative-path tested, observable/operable, linked to C073, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 44. Distributed tracing

**Audit mapping:** C074  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Adopt the platform trace context format (for example W3C Trace Context/OpenTelemetry) and document sampling policy.
- [ ] Create spans for reconcile, translate, identity/compatibility lookup, scheduler/resource-packer/runtime operations, status write, and significant retry waits.
- [ ] Propagate trace context through asynchronous work-queue handoff and downstream RPC metadata.
- [ ] Record bounded attributes: Kubernetes UID/generation, operation, peer, result/reason, site, config/policy version; avoid secrets/high-cardinality free text.
- [ ] Link retries/leader handoff where parent-child relationships cannot be preserved cleanly.
- [ ] Record errors with stable codes and do not duplicate sensitive exception bodies.
- [ ] Test propagation across success, retry, cancellation, timeout, and async queue paths.
- [ ] Verify sampling does not remove mandatory security audit records, which are a separate evidence stream.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Distributed tracing** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Distributed tracing is implemented, negative-path tested, observable/operable, linked to C074, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 45. Safe diagnostics and explain view

**Audit mapping:** C075-C077  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define a decision record schema capturing normalized input digest, identity mapping, policy/capability versions, constraints, translation result/refusal, downstream operation/result, and final status projection.
- [ ] Store only bounded/redacted diagnostic material; large labels/annotations/raw manifests require explicit opt-in and privacy review.
- [ ] Provide an operator command/API that explains why a workload was accepted/refused/degraded using stable reason codes and referenced policy versions.
- [ ] Make explain output distinguish facts/observations from policy decisions and derived conclusions.
- [ ] Include stale-data markers and observation timestamps so operators can see when a decision used cached information.
- [ ] Authorize diagnostic access by tenant/operator role and audit access to sensitive support data.
- [ ] Set retention/size bounds and deletion policy for decision records.
- [ ] Test secret redaction, cross-tenant access denial, pathological metadata size, and explanation reproducibility.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Safe diagnostics and explain view** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Safe diagnostics and explain view is implemented, negative-path tested, observable/operable, linked to C075-C077, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 46. Release/infrastructure correlation

**Audit mapping:** C078  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Assign each deployed INV-67 release a build/release lineage identifier tied to commit, image digest, SBOM/provenance, config digest, and manifest/chart version.
- [ ] Annotate Kubernetes Deployment/Pods and controller status/health output with the lineage ID.
- [ ] Attach lineage ID to logs, traces, audit events, and machine-readable acceptance evidence.
- [ ] Record relevant infrastructure/site/runtime versions for each decision or make them discoverable by immutable reference.
- [ ] Provide a query path from a workload UID to controller build, active config/policy, downstream runtime/site, and release evidence.
- [ ] Handle rolling upgrades by recording the exact replica/build that made each mutating decision.
- [ ] Test correlation across upgrade, rollback, leader handoff, and multi-site operation.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Release/infrastructure correlation** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Release/infrastructure correlation is implemented, negative-path tested, observable/operable, linked to C078, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 47. Telemetry policy, dashboards, and alerts

**Audit mapping:** C079-C080  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Write telemetry policy covering data classification, allowed attributes, retention, sampling, aggregation, export destinations, access, and deletion/privacy requirements.
- [ ] Create controller overview dashboard with reconcile rate/latency/errors, queue age/depth, leader state, API health, downstream health, readiness, and version/config.
- [ ] Create SLO/error-budget dashboard for translation/reconcile/status and dependency-related objectives.
- [ ] Alert on stale watch, queue-age breach, sustained refusal anomalies, retry/breaker saturation, dependency outage, leader thrash, audit sink failure, config rollback, and security attack indicators.
- [ ] Use multi-window burn-rate alerts for SLOs rather than static latency thresholds alone where applicable.
- [ ] Define severity, owner, runbook link, suppression/dedup, and expected operator action for every alert.
- [ ] Test alerts with synthetic/fault-injection scenarios and verify they clear after recovery.
- [ ] Review dashboards/alerts against incident postmortems and capacity changes.
- [ ] Define a stable telemetry schema with bounded-cardinality labels and correlation IDs spanning Kubernetes object, tenant, workload, operation, and downstream request.
- [ ] Emit RED/USE-style signals appropriate to the component and distinguish user errors, policy refusals, dependency faults, and software defects.
- [ ] Propagate trace context across asynchronous queues and downstream calls while preventing unbounded baggage growth.
- [ ] Document retention, sampling, privacy, redaction, and export behavior for metrics, logs, traces, and audit records.
- [ ] Provide operator views that expose current version, configuration digest, dependency health, queue/saturation state, and recent failure causes.

### Verification and negative-path checklist

- [ ] Generate each defined signal in an integration test and assert name/type/labels/reason/correlation fields.
- [ ] Verify telemetry remains bounded under high object cardinality and hostile/untrusted metadata.
- [ ] Verify redaction with sentinel secrets and authorization of detailed diagnostics.
- [ ] Exercise alert/dashboard conditions using fault injection and confirm runbook linkage.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Telemetry policy, dashboards, and alerts** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Telemetry policy, dashboards, and alerts is implemented, negative-path tested, observable/operable, linked to C079-C080, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase H — Testing and certification

## 48. Public contract/schema conformance tests

**Audit mapping:** C022, C029, C082  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Validate `PK_K8S_TRANSLATE/1`, `PK_K8S_REFUSE/1`, and `PK_K8S_STATUS/1` outputs with a real JSON Schema validator, not syntax parsing only.
- [ ] Create golden positive fixtures for minimum, representative, boundary, and maximum supported inputs.
- [ ] Create negative fixtures for missing required fields, wrong types, unknown properties where forbidden, invalid enums, negative/non-finite/oversized quantities, and malformed refusal details.
- [ ] Verify schema version and `$id` stability rules and ensure incompatible changes require a new version.
- [ ] Add round-trip/serialization tests to ensure canonical output does not depend on dict insertion order where signatures/digests are used.
- [ ] Maintain backward-compatibility fixtures for every supported contract version.
- [ ] Validate examples in README/docs automatically against schemas.
- [ ] Publish contract test artifacts for downstream consumers to run independently.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Public contract/schema conformance tests** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Public contract/schema conformance tests is implemented, negative-path tested, observable/operable, linked to C022, C029, C082, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 49. Adjacent-layer integration test environment

**Audit mapping:** C030, C083  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Provide deterministic test doubles for PLN-02, SCH-01, INV-68, GAP-15, runtime, secret/KMS, and audit/telemetry endpoints with fault controls.
- [ ] Provide an ephemeral Kubernetes environment (kind/k3d/envtest or equivalent) using real API machinery, RBAC, CRDs, status, finalizers, and leader election.
- [ ] Test end-to-end create→identity→compatibility→translate→place→runtime status→Kubernetes status→delete.
- [ ] Test refusal before side effects for unsupported/unauthorized/incompatible workloads.
- [ ] Test retries/timeouts/cancellation across every peer boundary and verify end-to-end deadlines.
- [ ] Test deletion during placement/start and runtime unknown state.
- [ ] Preserve peer request/response fixtures with protocol version and expected correlation IDs.
- [ ] Run a real-peer integration lane periodically or pre-release so mocks cannot drift from actual adjacent components.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Adjacent-layer integration test environment** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Adjacent-layer integration test environment is implemented, negative-path tested, observable/operable, linked to C030, C083, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 50. Kubernetes/runtime compatibility matrix tests

**Audit mapping:** C084, C093  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define the exact Kubernetes minor versions and API server configurations supported by policy.
- [ ] Run controller/CRD/install/integration suites against each supported Kubernetes version in CI or release certification.
- [ ] Test supported CPU architectures/OS/runtime providers where INV-67 behavior or downstream compatibility differs.
- [ ] Run protocol matrix tests across supported SCH-01/INV-68/PLN-02/GAP-15/runtime versions and declared skew windows.
- [ ] Test API feature differences, watch behavior, CEL/schema support, server-side apply, status/finalizer semantics, and RBAC across Kubernetes versions.
- [ ] Record matrix result, environment image/digest, and known limitations in release evidence.
- [ ] Block release when a supported cell is failing unless formally waived with expiry and impact.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Kubernetes/runtime compatibility matrix tests** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Kubernetes/runtime compatibility matrix tests is implemented, negative-path tested, observable/operable, linked to C084, C093, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 51. Fuzz/property-based parser tests

**Audit mapping:** C085  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Use property-based generation for Pod dictionaries within and outside the supported subset.
- [ ] Assert supported inputs either translate deterministically or fail only for documented validation constraints.
- [ ] Assert every unsupported semantic produces a stable structured refusal and never silently disappears.
- [ ] Generate quantity strings across valid SI/BinarySI/exponent forms plus malformed/oversized/Unicode/numeric edge cases.
- [ ] Generate labels/annotations with Kubernetes-valid/invalid boundary lengths and characters consistent with the intended validation contract.
- [ ] Fuzz deep/large nested objects and map/list cardinality to expose CPU/memory blowups.
- [ ] Persist minimal failing seeds/corpus cases and run them as deterministic regressions.
- [ ] Run coverage-guided fuzzing for pure translator code in an isolated resource-limited job if tooling permits.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Fuzz/property-based parser tests** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Fuzz/property-based parser tests is implemented, negative-path tested, observable/operable, linked to C085, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 52. Concurrency/race tests

**Audit mapping:** C086  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Run multiple reconcile workers against duplicate events for the same UID/generation and prove at-most-once external side effects through idempotency.
- [ ] Inject concurrent Kubernetes spec/status updates and stale resourceVersion conflicts.
- [ ] Test update followed immediately by delete, delete followed by name reuse/new UID, and rapid generation changes.
- [ ] Test leader handoff while work is in-flight and while downstream outcome is unknown.
- [ ] Test config reload and policy/capability version change during reconciliation.
- [ ] Run with race/concurrency instrumentation available to the language/runtime and deterministic barriers around critical sections.
- [ ] Assert final state converges, no workload crosses tenant/identity boundary, and no stuck finalizer remains.
- [ ] Repeat stress loops sufficiently to expose ordering-dependent failures and preserve seeds/traces for failures.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Concurrency/race tests** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Concurrency/race tests is implemented, negative-path tested, observable/operable, linked to C086, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 53. Benchmark/soak/burst/fleet-scale certification

**Audit mapping:** C088  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create sustained soak scenarios long enough to expose memory leaks, queue drift, credential refresh problems, watch reconnect issues, and telemetry growth.
- [ ] Create burst tests at multiples of expected event/reconcile rate and verify bounded queue/memory plus recovery time.
- [ ] Create fleet-scale object-count tests representative of maximum watched namespaces/pods/CRs.
- [ ] Include dependency latency/brownout and API throttling during load rather than benchmarking only ideal conditions.
- [ ] Measure fairness across tenants and priority of deletion/revocation during overload.
- [ ] Record p50/p95/p99/max latency, throughput, CPU/memory, API QPS, downstream QPS, queue age/depth, rejects, and recovery time.
- [ ] Store raw datasets and environment metadata; compare against release baseline and capacity model.
- [ ] Fail certification on SLO/capacity regression outside approved budget.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Benchmark/soak/burst/fleet-scale certification** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Benchmark/soak/burst/fleet-scale certification is implemented, negative-path tested, observable/operable, linked to C088, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 54. Machine-readable production acceptance evidence

**Audit mapping:** C090, C100  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define an evidence bundle schema containing release ID, commit, build/image digest, dependency lock digest, SBOM/provenance refs, config/schema versions, test suites/results, security scans, benchmarks, compatibility matrix, and approvals.
- [ ] Digitally sign or otherwise make the evidence bundle tamper-evident according to platform policy.
- [ ] Reference immutable artifact digests rather than mutable filenames/tags.
- [ ] Include explicit PASS/FAIL/WAIVED status per mandatory release gate and link waivers to owner/expiry.
- [ ] Include the traceability-matrix snapshot and checklist results produced from real CI execution.
- [ ] Store evidence in a durable release ledger accessible during incident/audit reconstruction.
- [ ] Validate evidence schema in CI and block promotion when mandatory fields/evidence are absent.
- [ ] Provide a verification command that independently checks signatures/digests and reports acceptance status.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Machine-readable production acceptance evidence** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Machine-readable production acceptance evidence is implemented, negative-path tested, observable/operable, linked to C090, C100, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 55. Executable full checklist gate in this archive

**Audit mapping:** C090, C100  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Declare `pk_core` and exact compatible version range in package metadata or vendor the minimal gate runtime if policy permits.
- [ ] Make the full checklist/conformance suite executable from a clean checkout without undocumented sibling-repository path assumptions.
- [ ] Replace skip-on-missing-core behavior in release CI with a hard failure for required conformance dependencies.
- [ ] Provide a documented developer mode where unavailable integration dependencies may skip, clearly separated from release mode.
- [ ] Pin checklist schema/version and fail if audit inputs drift unexpectedly.
- [ ] Emit machine-readable findings with evidence links/digests and nonzero exit on unmet mandatory requirements.
- [ ] Run the gate in both source tree and built/package artifact to detect packaging omissions.
- [ ] Document exact release command and preserve the gate output in the signed acceptance bundle.
- [ ] Use deterministic fixtures for success, invalid, unsupported, degraded, retryable, conflict, timeout, and cancellation paths.
- [ ] Run tests in normal and optimized Python modes where applicable and ensure correctness does not depend on assert side effects.
- [ ] Include negative and adversarial cases; passing happy-path tests alone is not acceptance evidence.
- [ ] Version test fixtures and expected wire/schema artifacts so compatibility regressions are reviewable.
- [ ] Make CI produce machine-readable test/evidence artifacts with artifact digests and tool versions.

### Verification and negative-path checklist

- [ ] Run the suite from a clean checkout and from the built release artifact; results must not depend on a developer workstation.
- [ ] Fail required release jobs on skip, missing dependency, flaky timeout, or absent evidence unless an explicit approved policy says otherwise.
- [ ] Preserve machine-readable results, environment metadata, fixtures/corpus versions, and artifact digests.
- [ ] Demonstrate that at least one intentionally broken build is rejected by the gate to prove the test/gate is effective.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Executable full checklist gate in this archive** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Executable full checklist gate in this archive is implemented, negative-path tested, observable/operable, linked to C090, C100, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase I — Operations, release, and governance

## 56. Supported-version/deprecation matrix

**Audit mapping:** C016, C093-C094  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Publish a table of supported Kubernetes minors, Python/runtime, pk_core, SCH-01, INV-68, PLN-02, GAP-15, runtime/protocol, Helm/Kustomize/operator bundle, and schema/CRD versions.
- [ ] For each entry, record minimum, maximum/currently tested, support tier, EOL date/policy, and known incompatibilities.
- [ ] Define N/N-1 or other version-skew policy across controller replicas and downstream peers.
- [ ] Define advance notice and migration guidance for deprecation/removal.
- [ ] Automate checks that release metadata matches the compatibility matrix and that unsupported combinations are rejected at startup or admission.
- [ ] Review the matrix on every Kubernetes/support release cycle and vulnerability-driven dependency update.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Supported-version/deprecation matrix** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Supported-version/deprecation matrix is implemented, negative-path tested, observable/operable, linked to C016, C093-C094, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 57. Vulnerability/patch response policy

**Audit mapping:** C094  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define vulnerability severity methodology and remediation SLA for critical/high/medium/low findings.
- [ ] Continuously scan Python dependencies, container base image, OS packages, IaC/Kubernetes manifests, and source where appropriate.
- [ ] Define triage rules for reachability/exploitability and document risk acceptance separately from scanner suppression.
- [ ] Define emergency patch/rebuild/release path with reduced but mandatory security/correctness gates.
- [ ] Define coordinated disclosure/contact process and ownership for externally reported vulnerabilities.
- [ ] Track upstream EOL and security support for Python/base image/dependencies/Kubernetes client stack.
- [ ] Require evidence that released images/artifacts are rescanned at promotion time or against current advisory data.
- [ ] Test key/certificate/revocation and emergency configuration procedures used during security response.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Vulnerability/patch response policy** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Vulnerability/patch response policy is implemented, negative-path tested, observable/operable, linked to C094, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 58. Backup/restore/reconstruction procedure

**Audit mapping:** C095  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Inventory durable state required by the final architecture: CRDs/status, configuration history, emergency controls, evidence/audit references, idempotency/operation ledger, and external runtime state.
- [ ] Classify which state is authoritative, reconstructable, cached, or ephemeral.
- [ ] Define backup responsibility, retention, encryption, integrity verification, and restore authorization for each durable store.
- [ ] Provide reconstruction procedure from Kubernetes desired state plus downstream query when local controller state is lost.
- [ ] Define behavior if audit/evidence history cannot be restored even though workload state can be reconstructed.
- [ ] Test full loss of controller local state, control-store restore, stale backup, partial store loss, and cross-version restore/migration.
- [ ] Measure RPO/RTO and include restore drill evidence in periodic certification.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Backup/restore/reconstruction procedure** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Backup/restore/reconstruction procedure is implemented, negative-path tested, observable/operable, linked to C095, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 59. Production runbooks

**Audit mapping:** C096  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Write command-complete Day-0 preflight/install/bootstrap with expected PASS signals and failure remediation.
- [ ] Write Day-1 deployment verification covering leader, readiness, RBAC, watch freshness, downstream connectivity, telemetry, audit sink, and a canary workload.
- [ ] Write upgrade/canary/rollback procedure with exact commands, checkpoints, and stop/rollback criteria.
- [ ] Write degraded-mode runbooks for Kubernetes API outage, scheduler/runtime outage, identity/compatibility outage, audit/telemetry failure, and secret/certificate expiry.
- [ ] Write queue saturation/stuck-finalizer/status-stall diagnosis and safe remediation.
- [ ] Write emergency freeze/quarantine and safe re-enable procedure.
- [ ] Write backup/reconstruction and leader/failover recovery procedure.
- [ ] Link every actionable alert to the relevant runbook section and validate commands during game days.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Production runbooks** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Production runbooks is implemented, negative-path tested, observable/operable, linked to C096, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 60. Incident response model

**Audit mapping:** C097  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define severity levels based on cross-tenant/security impact, workload outage, control-plane degradation, data/evidence integrity, and blast radius.
- [ ] Define paging/acknowledgement/escalation targets and incident commander/operations/security roles.
- [ ] Define immediate containment options including freeze/quarantine, credential revocation, policy rollback, deployment rollback, and traffic isolation.
- [ ] Define evidence preservation: audit logs, traces, Kubernetes events/objects, config/policy versions, controller lineage, downstream state, and time synchronization context.
- [ ] Define communications and stakeholder update cadence appropriate to severity.
- [ ] Define recovery verification and criteria for lifting containment.
- [ ] Require post-incident review with root cause, contributing factors, detection gap, corrective actions, owners, and deadlines.
- [ ] Feed corrective actions back into threat model, tests, alerts, runbooks, and exception ledger.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Incident response model** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Incident response model is implemented, negative-path tested, observable/operable, linked to C097, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 61. Recurring review program

**Audit mapping:** C098  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Establish scheduled reviews for RBAC/access, threat model, architecture ADRs, dependency/EOL, vulnerabilities, configuration/policy, SLO/capacity, runbooks, and waivers.
- [ ] Assign review cadence based on risk and change frequency, with event-triggered review after major incidents or architecture changes.
- [ ] Generate review evidence containing scope, inputs, findings, decisions, owners, and due dates.
- [ ] Automate reminders and flag overdue reviews in release governance.
- [ ] Revoke stale access and expired exceptions as part of reviews rather than only documenting them.
- [ ] Track recurring findings to identify systemic control failures.
- [ ] Require unresolved high-risk review findings to block or explicitly waive production promotion.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Recurring review program** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Recurring review program is implemented, negative-path tested, observable/operable, linked to C098, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 62. Exception/waiver/technical-debt ledger

**Audit mapping:** C099  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Create a machine-readable ledger with unique ID, affected requirement/control, scope, rationale, risk, owner, approver, compensating controls, creation date, expiry, and remediation target.
- [ ] Prohibit permanent/expiry-less waivers for mandatory security/reliability controls unless governance explicitly permits and records that decision.
- [ ] Link waivers to specific release/config/policy versions so scope does not silently expand.
- [ ] Surface active waivers in release evidence and operator/review dashboards.
- [ ] Fail CI/release when an applicable waiver is expired or missing approval.
- [ ] Require re-review when architecture, threat model, blast radius, or underlying risk changes.
- [ ] Close ledger entries only with verifiable remediation evidence; preserve historical record.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Exception/waiver/technical-debt ledger** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Exception/waiver/technical-debt ledger is implemented, negative-path tested, observable/operable, linked to C099, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 63. Formal release/exit gate

**Audit mapping:** C100  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Define mandatory gate categories: compile/unit, schema, static/type/security analysis, integration, compatibility matrix, adversarial tests, fault injection, benchmark/capacity, packaging/SBOM/provenance, install/upgrade/rollback, and evidence validation.
- [ ] Define which gates run on every change vs pre-merge/nightly/release due to cost, without allowing release to bypass required certification.
- [ ] Require clean source checkout and built-artifact verification so packaging errors are caught.
- [ ] Require all P0 requirements and release-critical traceability rows to be PASS or valid unexpired waiver.
- [ ] Require immutable artifact digests and signed evidence bundle before promotion.
- [ ] Require explicit approval roles for security, operations, and release owner where governance calls for human sign-off.
- [ ] Make promotion tooling consume gate results automatically rather than relying on manual interpretation of console logs.
- [ ] Provide a reproducible verification command that a separate reviewer can run on the candidate artifact.
- [ ] Document installation, upgrade, rollback, failure triage, degraded operation, recovery, and verification as command-complete runbooks.
- [ ] Define ownership, support hours/targets, escalation path, and incident severity criteria.
- [ ] Make every emergency control scoped, authenticated, authorized, audited, reversible, and safe under partial failure.
- [ ] Define evidence retention and review cadence for security, architecture, dependencies, SLOs, and operational exceptions.
- [ ] Require a formal release gate that references immutable build artifacts, test results, configuration schema, and approval evidence.

### Verification and negative-path checklist

- [ ] Run a game day/tabletop using the documented procedure with an operator who did not author it.
- [ ] Verify commands, permissions, rollback points, alerts, evidence capture, and escalation paths under degraded conditions.
- [ ] Track findings to owners/deadlines and update the runbook/governance artifact before marking complete.
- [ ] Archive dated drill/review evidence and reference it from the release/recurring-review system.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Formal release/exit gate** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Formal release/exit gate is implemented, negative-path tested, observable/operable, linked to C100, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Phase J — Packaging and repository engineering gaps

## 64. Standalone package metadata/dependency declaration

**Audit mapping:** Repository gap  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Add `pyproject.toml` with package name/version, Python compatibility, build backend, runtime dependencies, optional test/dev extras, license metadata, classifiers, and package data rules.
- [ ] Declare the compatible `pk_core` version/range required by `contract.py`/`component.py`; do not rely on sibling directory imports.
- [ ] Choose and document version source so `VERSION`, package metadata, and `__version__` cannot drift.
- [ ] Generate a deterministic lock or constraints file for release/test environments according to repository policy.
- [ ] Ensure schemas and required non-Python files are included in wheel/sdist/package manifests.
- [ ] Build wheel/sdist in CI and run tests from installed artifacts in a clean environment.
- [ ] Validate dependency conflicts and unsupported Python versions fail clearly during install/preflight.
- [ ] Document editable-development workflow separately from production installation.
- [ ] Pin toolchain/dependency policy and record exact versions used to build, test, scan, and package release artifacts.
- [ ] Generate deterministic manifests and checksums for shipped files and reject unexpected package contents.
- [ ] Include licensing, dependency inventory, SBOM, provenance, and vulnerability scan outputs in the release evidence set.
- [ ] Keep development-only dependencies and credentials out of runtime packages.
- [ ] Verify a clean checkout can reproduce the packaged artifact using documented commands.

### Verification and negative-path checklist

- [ ] Build/package from a clean checkout using only documented commands and protected CI inputs.
- [ ] Install/verify the artifact in a clean environment with no sibling-repository or user-site dependency leakage.
- [ ] Verify manifest/checksum/SBOM/provenance consistency against the exact shipped bytes.
- [ ] Record toolchain versions, artifact digests, scan results, and reproducibility result in release evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Standalone package metadata/dependency declaration** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Standalone package metadata/dependency declaration is implemented, negative-path tested, observable/operable, linked to Repository gap, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 65. CI workflow

**Audit mapping:** Repository gap  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Add repository-local CI triggered on pull request and protected-branch/release events.
- [ ] Run format/lint/type/static/security scans with pinned tool versions and configuration.
- [ ] Run compileall plus unit/schema tests in normal and `python -O` modes.
- [ ] Run package build/install tests from wheel/sdist in clean environments.
- [ ] Run Kubernetes integration/CRD/RBAC/controller tests and required adjacent-layer contract tests.
- [ ] Run adversarial/fuzz smoke, compatibility matrix, benchmark regression, and release-only fault/soak lanes according to cost tier.
- [ ] Generate SBOM, provenance, checksums, evidence bundle, and artifact attestations in protected release workflow.
- [ ] Enforce branch protection/required checks and prevent forks/untrusted PRs from accessing release secrets.
- [ ] Retain machine-readable artifacts/logs long enough for release/incident reconstruction.
- [ ] Pin toolchain/dependency policy and record exact versions used to build, test, scan, and package release artifacts.
- [ ] Generate deterministic manifests and checksums for shipped files and reject unexpected package contents.
- [ ] Include licensing, dependency inventory, SBOM, provenance, and vulnerability scan outputs in the release evidence set.
- [ ] Keep development-only dependencies and credentials out of runtime packages.
- [ ] Verify a clean checkout can reproduce the packaged artifact using documented commands.

### Verification and negative-path checklist

- [ ] Build/package from a clean checkout using only documented commands and protected CI inputs.
- [ ] Install/verify the artifact in a clean environment with no sibling-repository or user-site dependency leakage.
- [ ] Verify manifest/checksum/SBOM/provenance consistency against the exact shipped bytes.
- [ ] Record toolchain versions, artifact digests, scan results, and reproducibility result in release evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **CI workflow** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** CI workflow is implemented, negative-path tested, observable/operable, linked to Repository gap, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 66. License/NOTICE/SBOM/provenance bundle

**Audit mapping:** Repository gap  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Add an explicit project license file approved for the repository and ensure package metadata references it.
- [ ] Add NOTICE/third-party attribution material when required by chosen dependencies/licenses.
- [ ] Generate SPDX or CycloneDX SBOM for source/package/container release artifacts with exact dependency versions/digests.
- [ ] Generate build provenance/attestation recording source commit, builder identity, workflow, inputs, artifact digest, and build parameters.
- [ ] Scan license compatibility and prohibited dependency licenses in CI.
- [ ] Verify SBOM matches the built artifact rather than only the source environment.
- [ ] Package or publish license/SBOM/provenance references alongside every release artifact.
- [ ] Define retention and verification procedure for supply-chain evidence.
- [ ] Pin toolchain/dependency policy and record exact versions used to build, test, scan, and package release artifacts.
- [ ] Generate deterministic manifests and checksums for shipped files and reject unexpected package contents.
- [ ] Include licensing, dependency inventory, SBOM, provenance, and vulnerability scan outputs in the release evidence set.
- [ ] Keep development-only dependencies and credentials out of runtime packages.
- [ ] Verify a clean checkout can reproduce the packaged artifact using documented commands.

### Verification and negative-path checklist

- [ ] Build/package from a clean checkout using only documented commands and protected CI inputs.
- [ ] Install/verify the artifact in a clean environment with no sibling-repository or user-site dependency leakage.
- [ ] Verify manifest/checksum/SBOM/provenance consistency against the exact shipped bytes.
- [ ] Record toolchain versions, artifact digests, scan results, and reproducibility result in release evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **License/NOTICE/SBOM/provenance bundle** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** License/NOTICE/SBOM/provenance bundle is implemented, negative-path tested, observable/operable, linked to Repository gap, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 67. Static analysis/type checking configuration

**Audit mapping:** Repository gap  
**Priority:** P1  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Adopt pinned lint/type/security tools appropriate to Python and repository policy (for example Ruff/flake8, mypy/pyright, Bandit/Semgrep) with configuration committed to the repository.
- [ ] Set an initial clean baseline; suppressions must be inline/specific with rationale rather than blanket directory exclusions.
- [ ] Type public translator/component interfaces, structured error details, and configuration/protocol models sufficiently to catch shape drift.
- [ ] Enable checks for unsafe subprocess/path/deserialization/network/TLS patterns as implementation grows.
- [ ] Run dependency and secret scanners separately from source static analysis.
- [ ] Treat new high-confidence security/type errors as CI failures.
- [ ] Track technical-debt suppressions in the waiver/exception ledger when they affect production risk.
- [ ] Record tool versions and reports in release evidence.
- [ ] Pin toolchain/dependency policy and record exact versions used to build, test, scan, and package release artifacts.
- [ ] Generate deterministic manifests and checksums for shipped files and reject unexpected package contents.
- [ ] Include licensing, dependency inventory, SBOM, provenance, and vulnerability scan outputs in the release evidence set.
- [ ] Keep development-only dependencies and credentials out of runtime packages.
- [ ] Verify a clean checkout can reproduce the packaged artifact using documented commands.

### Verification and negative-path checklist

- [ ] Build/package from a clean checkout using only documented commands and protected CI inputs.
- [ ] Install/verify the artifact in a clean environment with no sibling-repository or user-site dependency leakage.
- [ ] Verify manifest/checksum/SBOM/provenance consistency against the exact shipped bytes.
- [ ] Record toolchain versions, artifact digests, scan results, and reproducibility result in release evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Static analysis/type checking configuration** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P1 DONE:** Static analysis/type checking configuration is implemented, negative-path tested, observable/operable, linked to Repository gap, and included in the signed or otherwise tamper-evident production acceptance bundle.

## 68. Release artifact manifest/checksums

**Audit mapping:** Repository gap  
**Priority:** P0  
**State at v4.2.0:** Missing or incomplete production implementation/evidence

### Design and implementation checklist

- [ ] Generate a canonical release manifest enumerating every shipped file/artifact with relative path, size, media/type, version, and SHA-256 or stronger digest.
- [ ] Include wheel/sdist/container/manifests/CRDs/charts/schemas/config examples/evidence/SBOM/provenance in the release set as applicable.
- [ ] Sign the manifest or attach a verifiable attestation from the protected release workflow.
- [ ] Verify the manifest against freshly downloaded/pulled artifacts before promotion.
- [ ] Fail release on unexpected files, missing files, checksum mismatch, or version inconsistency.
- [ ] Make checksum generation deterministic and platform-independent.
- [ ] Publish a verification command/script for operators and downstream automation.
- [ ] Preserve the manifest and signatures in the durable release/evidence ledger.
- [ ] Pin toolchain/dependency policy and record exact versions used to build, test, scan, and package release artifacts.
- [ ] Generate deterministic manifests and checksums for shipped files and reject unexpected package contents.
- [ ] Include licensing, dependency inventory, SBOM, provenance, and vulnerability scan outputs in the release evidence set.
- [ ] Keep development-only dependencies and credentials out of runtime packages.
- [ ] Verify a clean checkout can reproduce the packaged artifact using documented commands.

### Verification and negative-path checklist

- [ ] Build/package from a clean checkout using only documented commands and protected CI inputs.
- [ ] Install/verify the artifact in a clean environment with no sibling-repository or user-site dependency leakage.
- [ ] Verify manifest/checksum/SBOM/provenance consistency against the exact shipped bytes.
- [ ] Record toolchain versions, artifact digests, scan results, and reproducibility result in release evidence.

### Required completion evidence

- [ ] Version-controlled implementation/design artifacts for **Release artifact manifest/checksums** with code-review history.
- [ ] Automated test result(s) covering success, failure, and at least one adversarial/degraded path.
- [ ] Machine-readable evidence entry containing requirement IDs, artifact/test references, immutable digests, tool/environment versions, owner, and result.
- [ ] Operational/documentation update describing configuration, deployment, monitoring, rollback, and support implications where applicable.
- [ ] Traceability-matrix row(s) updated from `missing/partial` to `present` only after all required evidence is available.

### Acceptance gate

- [ ] **P0 DONE:** Release artifact manifest/checksums is implemented, negative-path tested, observable/operable, linked to Repository gap, and included in the signed or otherwise tamper-evident production acceptance bundle.

# Final integrated production-readiness gate

- [ ] All 68 component acceptance gates are PASS or have an explicitly permitted, approved, unexpired waiver in the exception ledger.
- [ ] The requirements traceability matrix has no mandatory orphan requirement and no `present` claim without immutable implementation/test evidence.
- [ ] The controller can be installed into a clean supported Kubernetes cluster using repository artifacts only and reaches readiness with all mandatory dependencies healthy.
- [ ] A representative workload completes create → authorization/identity → compatibility → translation → placement/runtime → status → deletion without manual repair.
- [ ] Unsupported, unauthorized, incompatible, unsafe, or unverifiable workloads are refused before irreversible side effects with stable machine-readable reasons.
- [ ] Controller restart, duplicate events, API watch reconnect, leader handoff, downstream outage, and reconnect converge without duplicate launch, lost cancellation, cross-tenant action, or leaked finalizer.
- [ ] Security tests, threat-model mitigations, RBAC, artifact verification, transport identity, secret handling, audit trail, and incident controls have current evidence.
- [ ] Performance/capacity certification satisfies the declared SLO envelope at the supported fleet size and stores reproducible raw/baseline evidence.
- [ ] Metrics/logs/traces/conditions/health endpoints and dashboards/alerts provide enough correlated evidence to diagnose every defined major failure class without exposing secrets.
- [ ] Install, upgrade, rollback, degraded-mode, emergency freeze, backup/reconstruction, and incident procedures have been exercised in a game day or automated environment.
- [ ] Wheel/package/container/deployment artifacts are reproducible enough for policy, contain expected files only, and ship with manifest, checksums, license/NOTICE, SBOM, provenance, and compatibility metadata.
- [ ] The full 100-item project gate runs without required skips in release mode and produces a machine-readable signed/tamper-evident evidence bundle.
- [ ] A separate reviewer can verify the release artifact and evidence bundle using documented commands without access to the original developer workstation.

## Sign-off record

| Role | Name/Identity | Decision | Date | Evidence/Approval Reference |
|---|---|---|---|---|
| INV-67 accountable owner |  |  |  |  |
| Platform/Kubernetes reviewer |  |  |  |  |
| Security reviewer |  |  |  |  |
| SRE/Operations reviewer |  |  |  |  |
| Downstream scheduler/runtime owner |  |  |  |  |
| Release authority |  |  |  |  |

---

**Generated from the v4.2.0 post-hardening audit.** This document intentionally treats production readiness as evidence-based: documentation, implementation, tests, deployment behavior, and release artifacts must agree before a component is closed.
