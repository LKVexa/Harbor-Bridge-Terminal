# INV-34 v5.0.0 — Comprehensive Missing-Component Implementation Checklist

## Purpose

This document expands every **Missing** or **Partial** item in the INV-34 v5.0.0 post-fix gap inventory into an implementation-grade closure checklist. It is intended for architecture, platform engineering, virtualization, SRE, security, test/certification, release engineering, and governance teams responsible for taking the corrected reference controller to a production-capable ACPI CPU hot-plug service.

The checklist preserves the v5.0.0 architectural correction: INV-34 is the **conventional VM CPU expansion path using ACPI CPU hot-plug**. It is **not** a CPU-feature-level classifier and it does **not** perform CPU hot-unplug.

## Non-negotiable global invariants

Every component below must preserve all of these invariants unless a future, separately approved architecture revision explicitly replaces them:

- [ ] CPU changes through INV-34 are monotonic hot-add only; no implementation path may silently introduce CPU hot-unplug.
- [ ] `desired_vcpus` and independently observed online `observed_vcpus` remain separate facts; request acceptance is never reported as guest convergence.
- [ ] New desired targets never exceed the configured VM maximum or authoritative allocatable host capacity/commitment policy.
- [ ] Unsupported hypervisor/guest hot-plug capability, unknown mandatory security state, or stale control-plane authority fails closed for new expansion.
- [ ] State generations/epochs and idempotency semantics prevent stale writers, duplicate client retries, replica races, and replay after restart from causing duplicate hot-plug.
- [ ] External side effects are fenced by current ownership/authority and are reconciled against live hypervisor/guest state after ambiguity or failure.
- [ ] Tenant/workload identity, authorization, quota, and isolation are enforced before production side effects.
- [ ] Every production-affecting decision can be traced to authenticated actor, request, VM, state generation, policy/configuration version, release artifact, adapter operation, and verification evidence.

## Checklist execution convention

Use these lifecycle values for each component: **Not Started → Designed → Implemented → Verified → Evidence Ready → Production Accepted**. A component is not closed merely because code exists. Closure requires its listed verification and evidence to be attached to the exact release artifact/configuration being promoted.

For each component, the `Checklist coverage` entries reproduce the production-gate requirement(s) that motivated the gap. Where a range is shown in the original inventory, every referenced requirement is included below.

---
## MC-001 — `pk_core` framework dependency or reproducible dependency lock/vendor strategy. The ZIP cannot execute its 100-item framework gate by itself.

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C016, C090, C100

### Objective

Make the package independently reproducible and make the `pk_core` production gate executable without undeclared local state.

### Referenced production requirements

- **INV-34-C016 — Requirements & Semantics:** Define versioning and backward-compatibility requirements for Legacy CPU expansion path.
- **INV-34-C090 — Testing & Certification:** Require machine-readable acceptance evidence before certifying a Legacy CPU expansion path release for production.
- **INV-34-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Make the package independently reproducible and make the `pk_core` production gate executable without undeclared local state

### Detailed technical checklist

- [ ] Choose exactly one supported dependency strategy: pinned package registry dependency, vendored immutable source, signed submodule, or documented bootstrap artifact.
- [ ] Pin `pk_core` to an immutable version/digest and record the compatibility range with INV-34 5.x.
- [ ] Add a lock file or equivalent transitive resolution record and test installation from a clean machine with no preexisting `pk_core`.
- [ ] Add an explicit optional-vs-required dependency boundary so standalone reference tests and production certification cannot be confused.
- [ ] Make framework-gate absence a hard production-certification failure while still allowing documented local unit tests to run.
- [ ] Capture the real `pk_core` gate output as signed/machine-readable evidence attached to the release.
- [ ] Add an offline/cache strategy for controlled environments and verify digest equality against the approved dependency.
- [ ] Add a negative CI job proving an unpinned, altered, or wrong-version `pk_core` cannot certify the release.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-002 — Named accountable service owner and escalation path (team/on-call/escalation destination).

**Current status:** Missing  
**Primary workstream:** Operations  
**Checklist coverage:** C009, C097

### Objective

Establish accountable ownership and an executable escalation chain for the CPU-expansion service.

### Referenced production requirements

- **INV-34-C009 — Architecture & Scope:** Assign an accountable owner and escalation path for Legacy CPU expansion path.
- **INV-34-C097 — Operations, Release & Governance:** Define incident severity, paging, escalation, containment, and recovery procedures.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Establish accountable ownership and an executable escalation chain for the CPU-expansion service

### Detailed technical checklist

- [ ] Record owning team/service name, primary owner role, secondary owner, and architecture/security/operations contacts.
- [ ] Define 24x7 or stated support coverage and identify the paging destination without embedding personal addresses in source.
- [ ] Define escalation timers by severity and the handoff path to hypervisor, guest OS, capability-discovery, and control-plane owners.
- [ ] Define authority to activate the emergency expansion kill switch and who may restore service afterward.
- [ ] Add owner metadata to service catalog/repository CODEOWNERS-equivalent and runbooks.
- [ ] Test the escalation path in a game day and retain acknowledgement timestamps and follow-up actions.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-003 — Formal SHALL-level requirements specification beyond contract prose, with stable requirement IDs for each CPU-expansion behavior.

**Current status:** Partial  
**Primary workstream:** Requirements  
**Checklist coverage:** C011-C019

### Objective

Replace prose-only intent with complete, stable SHALL-level CPU-expansion requirements.

### Referenced production requirements

- **INV-34-C011 — Requirements & Semantics:** Translate the source function of Legacy CPU expansion path — Conventional VM CPU scaling — into testable SHALL-level requirements.
- **INV-34-C012 — Requirements & Semantics:** Define functional requirements for Legacy CPU expansion path across cloud, datacenter, near-edge, and far-edge contexts where applicable.
- **INV-34-C013 — Requirements & Semantics:** Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.
- **INV-34-C014 — Requirements & Semantics:** Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Legacy CPU expansion path.
- **INV-34-C015 — Requirements & Semantics:** Define lifecycle states and legal state transitions managed or exposed by Legacy CPU expansion path.
- **INV-34-C016 — Requirements & Semantics:** Define versioning and backward-compatibility requirements for Legacy CPU expansion path.
- **INV-34-C017 — Requirements & Semantics:** Define capacity ceilings, quotas, and fairness semantics relevant to Legacy CPU expansion path.
- **INV-34-C018 — Requirements & Semantics:** Define behavior when network connectivity is intermittent or absent.
- **INV-34-C019 — Requirements & Semantics:** Define precedence rules when Legacy CPU expansion path requirements conflict with security, residency, SLO, or cost constraints.

### Required artifacts / deliverables

- [ ] Normative specification/ADR or policy document.
- [ ] Traceable requirement/test identifiers.
- [ ] Review/sign-off record.
- [ ] Component-specific design/implementation artifact demonstrating: Replace prose-only intent with complete, stable SHALL-level CPU-expansion requirements

### Detailed technical checklist

- [ ] Write SHALL statements for validation, monotonic expansion, configured maximum, host-capacity ceiling, capability gating, generation, idempotency, and convergence.
- [ ] Write SHALL NOT statements for hot-unplug, false convergence, stale generation acceptance, target-over-capacity, and unauthenticated/unauthorized execution.
- [ ] Define exact success/noop/pending/degraded/retryable/terminal semantics and legal state transitions.
- [ ] Define cloud/datacenter/near-edge/far-edge applicability and explicitly mark non-applicable contexts.
- [ ] Define latency, durability, consistency, isolation, and availability objectives with measurable units.
- [ ] Define network-disconnected behavior and requirement-precedence rules for security/residency/SLO/cost conflicts.
- [ ] Review every existing test and schema against the normative requirements; create a gap for any untested SHALL.
- [ ] Assign a directly responsible owner for this component and record approver, reviewer, and operational escalation roles.
- [ ] Define normative SHALL/SHALL NOT behavior, preconditions, postconditions, invariants, and externally visible failure semantics.
- [ ] Give every new requirement, interface field, policy rule, and acceptance criterion a stable identifier suitable for traceability.
- [ ] Document dependencies, trust boundaries, source-of-truth ownership, and behavior when an upstream fact is missing, stale, or contradictory.
- [ ] Define version/change-control rules so requirement changes cannot silently alter CPU-expansion safety semantics.
- [ ] Create positive, negative, boundary, and regression tests directly from the normative statements.
- [ ] Require peer review by architecture, security, operations, and test owners for changes that affect production semantics.
- [ ] Produce machine-readable closure evidence linking requirement IDs to implementation revision, test evidence, and approving release.

### Verification and negative-test checklist

- [ ] Demonstrate that every normative statement maps to at least one executable verification or an explicitly justified manual evidence control.
- [ ] Run an orphan check proving no mandatory requirement lacks implementation/evidence and no production behavior is undocumented.
- [ ] Review changes against backward-compatibility and operational-safety impact before approval.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-004 — Requirements traceability matrix mapping each requirement to source code, tests, schemas, operations evidence and release evidence.

**Current status:** Missing  
**Primary workstream:** Requirements  
**Checklist coverage:** C020

### Objective

Create a live requirements traceability matrix (RTM) connecting all requirements to implementation and evidence.

### Referenced production requirements

- **INV-34-C020 — Requirements & Semantics:** Maintain a requirements traceability matrix from each Legacy CPU expansion path requirement to implementation and verification evidence.

### Required artifacts / deliverables

- [ ] Normative specification/ADR or policy document.
- [ ] Traceable requirement/test identifiers.
- [ ] Review/sign-off record.
- [ ] Component-specific design/implementation artifact demonstrating: Create a live requirements traceability matrix (RTM) connecting all requirements to implementation and evidence

### Detailed technical checklist

- [ ] Create RTM rows for INV-34-C001..C100 and for all lower-level SHALL requirements introduced by component 3.
- [ ] Include source requirement ID, rationale, implementation file/symbol, schema/interface, unit/contract/integration test IDs, operations evidence, and release evidence.
- [ ] Allow one-to-many and many-to-one mappings without losing traceability; prohibit orphan requirements and orphan production behavior.
- [ ] Add automated checks that referenced files/tests exist and that every mandatory requirement has verification evidence.
- [ ] Include status values such as implemented, partial, externally dependent, waived, blocked, and retired with owner/expiry.
- [ ] Generate the RTM artifact during CI from source metadata where feasible to reduce manual drift.
- [ ] Make incomplete mandatory RTM rows block the production exit gate.
- [ ] Assign a directly responsible owner for this component and record approver, reviewer, and operational escalation roles.
- [ ] Define normative SHALL/SHALL NOT behavior, preconditions, postconditions, invariants, and externally visible failure semantics.
- [ ] Give every new requirement, interface field, policy rule, and acceptance criterion a stable identifier suitable for traceability.
- [ ] Document dependencies, trust boundaries, source-of-truth ownership, and behavior when an upstream fact is missing, stale, or contradictory.
- [ ] Define version/change-control rules so requirement changes cannot silently alter CPU-expansion safety semantics.
- [ ] Create positive, negative, boundary, and regression tests directly from the normative statements.
- [ ] Require peer review by architecture, security, operations, and test owners for changes that affect production semantics.
- [ ] Produce machine-readable closure evidence linking requirement IDs to implementation revision, test evidence, and approving release.

### Verification and negative-test checklist

- [ ] Demonstrate that every normative statement maps to at least one executable verification or an explicitly justified manual evidence control.
- [ ] Run an orphan check proving no mandatory requirement lacks implementation/evidence and no production behavior is undocumented.
- [ ] Review changes against backward-compatibility and operational-safety impact before approval.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-005 — Concrete hypervisor CPU-hotplug adapter (for example, a supported hypervisor API implementation) that translates desired state into ACPI CPU-hotplug operations.

**Current status:** Missing  
**Primary workstream:** Integration  
**Checklist coverage:** C021, C030, C031, C040, C083, C084

### Objective

Implement a real hypervisor adapter that translates accepted desired vCPU state into ACPI CPU hot-plug actions.

### Referenced production requirements

- **INV-34-C021 — Interfaces & Integration:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Legacy CPU expansion path.
- **INV-34-C030 — Interfaces & Integration:** Create automated integration tests proving Legacy CPU expansion path interoperates with adjacent architectural layers.
- **INV-34-C031 — Implementation & Configuration:** Select and pin approved implementations, versions, or specifications for Legacy CPU expansion path: ACPI hot-plug.
- **INV-34-C040 — Implementation & Configuration:** Provide a deterministic bootstrap path from an empty node/environment to healthy Legacy CPU expansion path operation.
- **INV-34-C083 — Testing & Certification:** Create integration tests with every supported adjacent layer and execution tier.
- **INV-34-C084 — Testing & Certification:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Implement a real hypervisor adapter that translates accepted desired vCPU state into ACPI CPU hot-plug actions

### Detailed technical checklist

- [ ] Define an adapter interface such as `ensure_vcpus(vm_id, target_vcpus, generation, operation_id, deadline)` with typed result/error objects.
- [ ] Select the initial supported hypervisor/API and implement only documented CPU hot-add primitives; do not synthesize hot-unplug.
- [ ] Query current hypervisor CPU topology/count immediately before action and reconcile with durable desired/observed state.
- [ ] Use an operation/fencing token so a stale controller cannot repeat or supersede a newer hot-plug operation.
- [ ] Map already-at-target into idempotent success/noop and distinguish submitted, acknowledged, partially applied, failed, and unknown outcomes.
- [ ] Enforce backend timeouts and cancellation without assuming cancellation means the hypervisor did not perform the action.
- [ ] Capture backend operation IDs and normalized error codes for later observation and audit correlation.
- [ ] Add adapter-specific rate/concurrency limits and bounded retry policy based on documented hypervisor guarantees.
- [ ] Create integration fixtures against the real API plus a deterministic emulator for CI fault scenarios.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-006 — Guest CPU-online observation adapter that independently reports how many added CPUs the guest actually brought online.

**Current status:** Missing  
**Primary workstream:** Integration  
**Checklist coverage:** C021, C030, C051-C057, C071

### Objective

Implement an independent guest/hypervisor observation path for actual online-vCPU state.

### Referenced production requirements

- **INV-34-C021 — Interfaces & Integration:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Legacy CPU expansion path.
- **INV-34-C030 — Interfaces & Integration:** Create automated integration tests proving Legacy CPU expansion path interoperates with adjacent architectural layers.
- **INV-34-C051 — Resilience & Failure Handling:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Legacy CPU expansion path.
- **INV-34-C052 — Resilience & Failure Handling:** Define automated health and stall detection thresholds for Legacy CPU expansion path.
- **INV-34-C053 — Resilience & Failure Handling:** Implement bounded retry with backoff and jitter only where operations are safe to retry.
- **INV-34-C054 — Resilience & Failure Handling:** Implement admission control, load shedding, or circuit breaking to prevent Legacy CPU expansion path failure cascades.
- **INV-34-C055 — Resilience & Failure Handling:** Define failover behavior without violating isolation, residency, or consistency requirements.
- **INV-34-C056 — Resilience & Failure Handling:** Provide degraded operation when noncritical dependencies are unavailable.
- **INV-34-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Legacy CPU expansion path state.
- **INV-34-C071 — Observability & Explainability:** Expose Legacy CPU expansion path health, readiness, version, configuration, dependency status, and active capability set.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Implement an independent guest/hypervisor observation path for actual online-vCPU state

### Detailed technical checklist

- [ ] Define observation source priority and trust rules: guest agent/kernel, hypervisor inventory, or both, and document disagreement handling.
- [ ] Emit observations with VM identity, online-vCPU count, source, source timestamp, monotonic observation sequence/generation, and confidence/health.
- [ ] Authenticate observation producers and reject observations for the wrong tenant/VM or from stale/untrusted sources.
- [ ] Distinguish presented CPUs from guest-online CPUs; convergence requires the configured authoritative online definition.
- [ ] Handle delayed/partial onlining without regressing observed count or claiming terminal failure prematurely.
- [ ] Detect impossible observations such as count above desired or below previous observed and route them to quarantine/incident handling.
- [ ] Define observation freshness TTL and behavior when the source is unavailable or stale.
- [ ] Add cross-check tests where hypervisor reports attached CPUs but guest reports fewer online CPUs.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-007 — Concrete ACPI/hypervisor specification pin : approved ACPI revision, hypervisor machine type/API version and adapter version.

**Current status:** Missing  
**Primary workstream:** Integration  
**Checklist coverage:** C016, C027, C031, C093

### Objective

Pin the exact ACPI and hypervisor execution specifications used by production adapters.

### Referenced production requirements

- **INV-34-C016 — Requirements & Semantics:** Define versioning and backward-compatibility requirements for Legacy CPU expansion path.
- **INV-34-C027 — Interfaces & Integration:** Define compatibility behavior when peers use different supported versions.
- **INV-34-C031 — Implementation & Configuration:** Select and pin approved implementations, versions, or specifications for Legacy CPU expansion path: ACPI hot-plug.
- **INV-34-C093 — Operations, Release & Governance:** Maintain a supported-version compatibility matrix for Legacy CPU expansion path and adjacent dependencies.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Pin the exact ACPI and hypervisor execution specifications used by production adapters

### Detailed technical checklist

- [ ] Record approved ACPI revision and the exact CPU hot-plug mechanism/events relied upon by the adapter.
- [ ] Pin hypervisor product/version, machine type/chipset, management API version, adapter version, and firmware/UEFI/BIOS assumptions.
- [ ] Document any vendor-specific deviations, feature flags, CPU-slot limits, topology restrictions, or reboot prerequisites.
- [ ] Add automated startup compatibility checks that refuse unsupported major/minor API or machine-type combinations.
- [ ] Version the specification profile independently from service code so compatibility changes are explicit.
- [ ] Capture vendor documentation references and test evidence for each pinned combination in the compatibility matrix.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-008 — Supported hypervisor/guest compatibility matrix with tested versions, architectures, machine types, firmware and known limitations.

**Current status:** Missing  
**Primary workstream:** Integration  
**Checklist coverage:** C027, C031, C084, C093

### Objective

Maintain a tested support matrix across hypervisor, machine type, firmware, architecture, guest OS/kernel, and adapter versions.

### Referenced production requirements

- **INV-34-C027 — Interfaces & Integration:** Define compatibility behavior when peers use different supported versions.
- **INV-34-C031 — Implementation & Configuration:** Select and pin approved implementations, versions, or specifications for Legacy CPU expansion path: ACPI hot-plug.
- **INV-34-C084 — Testing & Certification:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Legacy CPU expansion path.
- **INV-34-C093 — Operations, Release & Governance:** Maintain a supported-version compatibility matrix for Legacy CPU expansion path and adjacent dependencies.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Maintain a tested support matrix across hypervisor, machine type, firmware, architecture, guest OS/kernel, and adapter versions

### Detailed technical checklist

- [ ] Define matrix axes and the exact meaning of Supported, Experimental, Deprecated, Blocked, and Untested.
- [ ] List minimum/maximum tested versions rather than broad vendor families.
- [ ] Include vCPU start/max limits, topology constraints, ACPI/guest-online behavior, known defects, and required guest settings.
- [ ] Run automated matrix tests for every production-supported row and retain environment fingerprints.
- [ ] Make unsupported combinations fail closed before accepting a real expansion request.
- [ ] Add deprecation dates and migration guidance for rows approaching end of support.
- [ ] Link each supported row to contract/integration/performance/security evidence.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-009 — Real request transport/API boundary (RPC/HTTP/event/control-plane handler) implementing the bundled request/result/status contracts.

**Current status:** Missing  
**Primary workstream:** Integration  
**Checklist coverage:** C021-C022, C029-C030

### Objective

Expose a real authenticated control-plane transport that implements request/result/status contracts.

### Referenced production requirements

- **INV-34-C021 — Interfaces & Integration:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Legacy CPU expansion path.
- **INV-34-C022 — Interfaces & Integration:** Use versioned typed schemas for all externally visible Legacy CPU expansion path contracts.
- **INV-34-C029 — Interfaces & Integration:** Provide reference examples and conformance fixtures for Legacy CPU expansion path.
- **INV-34-C030 — Interfaces & Integration:** Create automated integration tests proving Legacy CPU expansion path interoperates with adjacent architectural layers.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Expose a real authenticated control-plane transport that implements request/result/status contracts

### Detailed technical checklist

- [ ] Choose RPC/HTTP/event semantics and define synchronous acceptance versus asynchronous convergence explicitly.
- [ ] Implement endpoints/methods for submit expansion, read status, and—if required—administrative freeze/resume without exposing hot-unplug.
- [ ] Validate JSON/protobuf/etc. schema version, identifier length, integer range, expected generation, idempotency key, and target before side effects.
- [ ] Carry deadline/cancellation and request-id metadata end to end; define maximum body/header/message sizes.
- [ ] Return stable machine-readable error code, retryability, correlation ID, and structured context without leaking secrets.
- [ ] Implement authentication, authorization, per-principal rate limiting, and tenant scoping at the transport edge.
- [ ] Add OpenAPI/protobuf/WIT equivalent artifacts and generated conformance fixtures where appropriate.
- [ ] Add transport-level fuzzing and malformed/framing/oversized message tests.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-010 — Authentication for callers, nodes, adapters and observation sources.

**Current status:** Missing  
**Primary workstream:** Security  
**Checklist coverage:** C023, C044

### Objective

Authenticate every caller, controller, node, adapter, and observation producer before trust is granted.

### Referenced production requirements

- **INV-34-C023 — Interfaces & Integration:** Define authentication requirements at each Legacy CPU expansion path boundary.
- **INV-34-C044 — Security, Trust & Isolation:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.

### Required artifacts / deliverables

- [ ] Threat/control design.
- [ ] Enforcement implementation/policy.
- [ ] Security tests and audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Authenticate every caller, controller, node, adapter, and observation producer before trust is granted

### Detailed technical checklist

- [ ] Define principal types and accepted credentials for user/control-plane, service-to-service, node, hypervisor adapter, and observer.
- [ ] Prefer workload identity/mTLS or equivalent short-lived credentials over static shared secrets.
- [ ] Bind authenticated identity to tenant/site/environment and reject identity/VM-scope mismatches.
- [ ] Validate certificate/token issuer, audience, subject, expiry, revocation status, and clock-skew policy.
- [ ] Define bootstrap trust roots and rotation/revocation procedures with overlap windows that do not permit indefinite old credentials.
- [ ] Fail closed when the identity service or revocation data is unavailable beyond the approved grace policy.
- [ ] Log authentication outcome using stable principal IDs without recording raw tokens or private keys.
- [ ] Add tests for expired, future, revoked, wrong-audience, wrong-tenant, forged, and replayed credentials.
- [ ] Document assets, principals, trust boundaries, abuse cases, attacker capabilities, and explicit security invariants for the component.
- [ ] Use least-privilege identities and capabilities; prohibit ambient filesystem, network, hypervisor, secret, or cross-tenant authority.
- [ ] Fail closed when identity, authorization, policy, key, attestation, provenance, or trusted-time decisions cannot be established.
- [ ] Define secret/key lifecycle requirements including source, rotation, revocation, memory handling, redaction, and incident response.
- [ ] Generate immutable/tamper-evident audit records for security-relevant state changes and administrative overrides.
- [ ] Add abuse-rate limits and resource bounds that prevent resource-exhaustion attacks from bypassing VM/host capacity safeguards.
- [ ] Derive adversarial tests from the threat model and run them automatically in CI or the certification environment.
- [ ] Require security review evidence and explicit residual-risk/exception records before production enablement.

### Verification and negative-test checklist

- [ ] Run unauthorized, cross-tenant, replay, stale, forged identity/data, exhaustion, and dependency-unavailable cases.
- [ ] Verify all deny/fail-closed paths generate appropriate audit evidence without secret leakage.
- [ ] Have an independent security reviewer verify least privilege and residual-risk disposition.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-011 — Authorization/capability enforcement tying expansion rights to tenant/workload/VM identity and least-privilege policy.

**Current status:** Missing  
**Primary workstream:** Security  
**Checklist coverage:** C024, C042, C046

### Objective

Enforce least-privilege authorization and explicit CPU-expansion capabilities per tenant/workload/VM.

### Referenced production requirements

- **INV-34-C024 — Interfaces & Integration:** Define authorization and explicit capability requirements at each Legacy CPU expansion path boundary.
- **INV-34-C042 — Security, Trust & Isolation:** Apply least privilege to every identity and capability used by Legacy CPU expansion path.
- **INV-34-C046 — Security, Trust & Isolation:** Enforce tenant/workload isolation across Legacy CPU expansion path execution, memory, state, network, and device boundaries as applicable.

### Required artifacts / deliverables

- [ ] Threat/control design.
- [ ] Enforcement implementation/policy.
- [ ] Security tests and audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Enforce least-privilege authorization and explicit CPU-expansion capabilities per tenant/workload/VM

### Detailed technical checklist

- [ ] Define authorization decision inputs: principal, tenant, VM, requested target, site/environment, quota, policy version, and current state.
- [ ] Define capabilities separately for request, status-read, freeze, resume, override, and administrative reconciliation.
- [ ] Prohibit wildcard fleet-wide expansion privilege for normal service identities; isolate break-glass privileges.
- [ ] Evaluate authorization immediately before accepting desired-state changes and record policy decision ID/version.
- [ ] Ensure adapter credentials cannot authorize a request; execution identities should only realize already-authorized desired state.
- [ ] Define behavior for policy-engine timeout/staleness and fail closed for new expansions.
- [ ] Add cross-tenant, confused-deputy, privilege-escalation, stale-policy, and break-glass audit tests.
- [ ] Document assets, principals, trust boundaries, abuse cases, attacker capabilities, and explicit security invariants for the component.
- [ ] Use least-privilege identities and capabilities; prohibit ambient filesystem, network, hypervisor, secret, or cross-tenant authority.
- [ ] Fail closed when identity, authorization, policy, key, attestation, provenance, or trusted-time decisions cannot be established.
- [ ] Define secret/key lifecycle requirements including source, rotation, revocation, memory handling, redaction, and incident response.
- [ ] Generate immutable/tamper-evident audit records for security-relevant state changes and administrative overrides.
- [ ] Add abuse-rate limits and resource bounds that prevent resource-exhaustion attacks from bypassing VM/host capacity safeguards.
- [ ] Derive adversarial tests from the threat model and run them automatically in CI or the certification environment.
- [ ] Require security review evidence and explicit residual-risk/exception records before production enablement.

### Verification and negative-test checklist

- [ ] Run unauthorized, cross-tenant, replay, stale, forged identity/data, exhaustion, and dependency-unavailable cases.
- [ ] Verify all deny/fail-closed paths generate appropriate audit evidence without secret leakage.
- [ ] Have an independent security reviewer verify least privilege and residual-risk disposition.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-012 — Quota and fairness service. Per-VM and host ceilings exist, but tenant/site/fleet quotas and fairness are absent.

**Current status:** Partial  
**Primary workstream:** State Config  
**Checklist coverage:** C017, C054, C067

### Objective

Implement tenant/site/fleet quota and fairness controls in addition to existing VM/host ceilings.

### Referenced production requirements

- **INV-34-C017 — Requirements & Semantics:** Define capacity ceilings, quotas, and fairness semantics relevant to Legacy CPU expansion path.
- **INV-34-C054 — Resilience & Failure Handling:** Implement admission control, load shedding, or circuit breaking to prevent Legacy CPU expansion path failure cascades.
- **INV-34-C067 — Performance & Resource Efficiency:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement tenant/site/fleet quota and fairness controls in addition to existing VM/host ceilings

### Detailed technical checklist

- [ ] Define quota dimensions such as vCPU total, expansion delta, concurrent pending expansions, request rate, and host/site reserve.
- [ ] Define hierarchy and precedence among workload, tenant, project, site, and fleet quotas.
- [ ] Choose fairness algorithm (for example weighted fair queueing or deficit round-robin) for contended expansion admission.
- [ ] Reserve capacity for control/system workloads if required and document starvation-prevention behavior.
- [ ] Make quota decisions atomic with durable desired-state admission to prevent oversubscription races.
- [ ] Expose quota remaining, rejection reason, queue position if queued, and policy version to operators.
- [ ] Test simultaneous tenants competing for the final available capacity and prove deterministic/fair outcomes.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-013 — Timeout, cancellation, retry and backpressure contract. Idempotency exists locally; transport/backend timeout/cancel/backpressure semantics do not.

**Current status:** Partial  
**Primary workstream:** Integration  
**Checklist coverage:** C025, C053-C054

### Objective

Complete transport/backend timeout, cancellation, retry, idempotency, and backpressure semantics.

### Referenced production requirements

- **INV-34-C025 — Interfaces & Integration:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Legacy CPU expansion path.
- **INV-34-C053 — Resilience & Failure Handling:** Implement bounded retry with backoff and jitter only where operations are safe to retry.
- **INV-34-C054 — Resilience & Failure Handling:** Implement admission control, load shedding, or circuit breaking to prevent Legacy CPU expansion path failure cascades.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Complete transport/backend timeout, cancellation, retry, idempotency, and backpressure semantics

### Detailed technical checklist

- [ ] Define separate deadlines for request admission, state-store transaction, authorization, adapter call, observation convergence, and status reads.
- [ ] Define cancellation points and explicitly state when cancellation stops waiting but cannot reverse a hot-plug side effect.
- [ ] Classify every error as retryable, terminal, unknown-outcome, or operator-action-required.
- [ ] Use durable idempotency across client retries and controller restarts; scope keys to caller/tenant/VM as appropriate.
- [ ] Define queue capacity, max in-flight requests, per-VM serialization, and overload rejection status/code.
- [ ] Propagate backpressure rather than unboundedly buffering work in transport or reconciler layers.
- [ ] Add deadline-race tests where the hypervisor completes just before/after timeout or cancellation.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-014 — Cross-version protocol compatibility behavior. Schemas are versioned, but downgrade/upgrade/coexistence rules are not implemented.

**Current status:** Partial  
**Primary workstream:** Integration  
**Checklist coverage:** C016, C027, C093

### Objective

Implement backward/forward protocol compatibility and mixed-version coexistence rules.

### Referenced production requirements

- **INV-34-C016 — Requirements & Semantics:** Define versioning and backward-compatibility requirements for Legacy CPU expansion path.
- **INV-34-C027 — Interfaces & Integration:** Define compatibility behavior when peers use different supported versions.
- **INV-34-C093 — Operations, Release & Governance:** Maintain a supported-version compatibility matrix for Legacy CPU expansion path and adjacent dependencies.

### Required artifacts / deliverables

- [ ] Versioned interface/schema or adapter contract.
- [ ] Concrete implementation plus conformance fixtures.
- [ ] Compatibility/error mapping documentation.
- [ ] Component-specific design/implementation artifact demonstrating: Implement backward/forward protocol compatibility and mixed-version coexistence rules

### Detailed technical checklist

- [ ] Define supported request/result/status schema versions and which side performs negotiation.
- [ ] Define additive vs breaking field rules, unknown-field handling, enum evolution, defaulting, and required-field introduction policy.
- [ ] Define rolling-upgrade behavior when old and new controllers/adapters coexist.
- [ ] Prevent older peers from silently ignoring safety-critical fields such as generation, tenant scope, or policy version.
- [ ] Provide translators only where semantics are lossless; reject unsafe downgrade paths.
- [ ] Add golden fixtures for N/N-1 and every explicitly supported cross-version pair.
- [ ] Document support windows and retirement dates in the compatibility matrix.
- [ ] Define the boundary as a versioned typed contract with explicit request, response, status, error, correlation, deadline, and capability fields.
- [ ] Specify ownership of connection/session lifecycle, concurrency, queueing, payload limits, cancellation, retry, and idempotency behavior.
- [ ] Map every remote/backend failure into stable machine-readable errors without conflating request acceptance with guest CPU convergence.
- [ ] Validate every boundary input before side effects; reject malformed, ambiguous, unsupported, stale, or over-limit input fail closed.
- [ ] Authenticate and authorize each principal crossing the boundary and bind authorization to VM/tenant/workload identity.
- [ ] Propagate request ID, VM ID, generation, trace context, adapter operation ID, and release/configuration lineage across the boundary.
- [ ] Provide conformance fixtures and contract tests for all supported versions, including downgrade/upgrade and mixed-version cases.
- [ ] Instrument rate, errors, timeout, retries, queue depth, saturation, and end-to-end convergence latency for this boundary.

### Verification and negative-test checklist

- [ ] Run success, noop, invalid input, stale generation, over-capacity, unsupported capability, timeout, cancellation, duplicate retry, and mixed-version cases through the real boundary.
- [ ] Inject dependency errors and unknown outcomes; verify stable error normalization and no false convergence/double hot-add.
- [ ] Verify tenant/VM identity and correlation metadata remain correct across every hop.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-015 — Declarative production configuration source for per-site/per-environment policy, maximums, adapter selection and enablement.

**Current status:** Missing  
**Primary workstream:** State Config  
**Checklist coverage:** C033, C035

### Objective

Create declarative production configuration for policy, ceilings, adapter selection, and enablement.

### Referenced production requirements

- **INV-34-C033 — Implementation & Configuration:** Define declarative configuration and secure defaults for Legacy CPU expansion path.
- **INV-34-C035 — Implementation & Configuration:** Support site- and environment-specific configuration without rebuilding immutable artifacts.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Create declarative production configuration for policy, ceilings, adapter selection, and enablement

### Detailed technical checklist

- [ ] Define a versioned configuration schema with environment/site/tenant-safe override rules.
- [ ] Include expansion enable flag, adapter type/version, request/queue/retry limits, convergence timeout, quota policy references, and telemetry settings.
- [ ] Keep per-VM mutable desired/observed state out of static configuration.
- [ ] Define secure defaults: expansion disabled until required authn/authz/adapter/observer dependencies are healthy.
- [ ] Validate all units/ranges and reject unknown security-critical keys unless explicitly supported.
- [ ] Support environment/site variation through configuration layering without rebuilding the code artifact.
- [ ] Add config lint and dry-run output showing effective configuration and provenance before activation.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-016 — Configuration provenance record containing version, author/actor, approval, activation time and source digest.

**Current status:** Missing  
**Primary workstream:** State Config  
**Checklist coverage:** C036

### Objective

Record tamper-resistant configuration provenance for every active configuration.

### Referenced production requirements

- **INV-34-C036 — Implementation & Configuration:** Record configuration provenance, version, author, and activation time.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Record tamper-resistant configuration provenance for every active configuration

### Detailed technical checklist

- [ ] Record configuration ID/version, content digest, source repository/path, author/actor identity, reviewer/approval, build/release linkage, and activation timestamp.
- [ ] Record previous configuration digest and activation generation to create a verifiable change chain.
- [ ] Capture effective merged configuration after overlays while preserving source-layer provenance.
- [ ] Expose provenance in health/explain endpoints and attach it to every expansion decision/audit event.
- [ ] Protect provenance records from ordinary service mutation and define retention equal to or longer than incident-analysis needs.
- [ ] Add tests proving two semantically different configs cannot share the same digest/identity and stale activation is rejected.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-017 — Atomic configuration activation / transactional update mechanism for multi-field policy changes.

**Current status:** Missing  
**Primary workstream:** State Config  
**Checklist coverage:** C037

### Objective

Apply production configuration updates atomically and transactionally.

### Referenced production requirements

- **INV-34-C037 — Implementation & Configuration:** Apply atomic or transactional configuration updates where partial application is unsafe.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Apply production configuration updates atomically and transactionally

### Detailed technical checklist

- [ ] Define the transaction boundary for multi-field updates such as enablement, ceilings, quota rules, adapter version, and retry policy.
- [ ] Validate the entire candidate configuration before changing any live field.
- [ ] Use generation/CAS semantics so concurrent administrators cannot overwrite each other silently.
- [ ] Publish one atomic activation marker only after all dependent components can consume the new configuration.
- [ ] On failure, retain the previous active generation and mark the candidate rejected with reason/evidence.
- [ ] Ensure in-flight expansion operations retain a well-defined policy/config generation for auditability.
- [ ] Add fault tests at every activation phase to prove no mixed partial configuration becomes active.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-018 — Rollback implementation. Operational guidance exists, but no executable rollback/controller-state restoration mechanism exists.

**Current status:** Partial  
**Primary workstream:** State Config  
**Checklist coverage:** C038, C092, C095

### Objective

Implement executable rollback for code, configuration, and controller state without corrupting live VM truth.

### Referenced production requirements

- **INV-34-C038 — Implementation & Configuration:** Define automatic and operator-driven rollback for failed Legacy CPU expansion path changes.
- **INV-34-C092 — Operations, Release & Governance:** Define canary, staged rollout, rollback, and emergency-disable procedures for Legacy CPU expansion path.
- **INV-34-C095 — Operations, Release & Governance:** Provide backup, restore, migration, or reconstruction procedures for Legacy CPU expansion path state where applicable.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement executable rollback for code, configuration, and controller state without corrupting live VM truth

### Detailed technical checklist

- [ ] Define rollback units separately for binary/image, configuration generation, adapter version, and durable controller schema.
- [ ] Never blindly roll observed/desired vCPU counts backward; reconcile restored state against live hypervisor/guest observations first.
- [ ] Create migration/rollback compatibility checks that block downgrade when the older version cannot interpret durable records safely.
- [ ] Automate configuration rollback to the previous signed generation with CAS and audit event.
- [ ] Define pending-operation handling during rollback: drain, fence, adopt, or quarantine with explicit rules.
- [ ] Exercise rollback after partial hot-plug, controller restart, and schema migration in staging/certification.
- [ ] Capture rollback success criteria and post-rollback convergence verification automatically.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-019 — Durable shared state store with compare-and-swap/transaction semantics for desired/observed state and generation across process restarts and multiple controllers.

**Current status:** Missing  
**Primary workstream:** State Config  
**Checklist coverage:** C032, C037, C057-C058

### Objective

Add durable shared state with transactional/CAS semantics for desired, observed, generation, and operation metadata.

### Referenced production requirements

- **INV-34-C032 — Implementation & Configuration:** Separate immutable artifacts from mutable configuration and state for Legacy CPU expansion path.
- **INV-34-C037 — Implementation & Configuration:** Apply atomic or transactional configuration updates where partial application is unsafe.
- **INV-34-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Legacy CPU expansion path state.
- **INV-34-C058 — Resilience & Failure Handling:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Add durable shared state with transactional/CAS semantics for desired, observed, generation, and operation metadata

### Detailed technical checklist

- [ ] Define a normalized per-VM record including tenant/site, desired_vcpus, observed_vcpus, max_vcpus snapshot/reference, host-capacity evidence, generation, pending operation, and timestamps.
- [ ] Choose a strongly consistent transaction primitive sufficient to serialize desired-state acceptance per VM.
- [ ] Use CAS on generation and/or lease fencing token for every mutation; reject stale writers deterministically.
- [ ] Define durability/replication settings and explicitly document acceptable data-loss and unavailability modes.
- [ ] Encrypt sensitive metadata at rest and restrict keys/namespaces by service role and tenant where applicable.
- [ ] Define schema migration and mixed-version read/write rules.
- [ ] Add crash-consistency tests around transaction commit, process death, network ambiguity, and replica failover.
- [ ] Export store latency/error/saturation metrics and surface stale/unavailable state as readiness degradation.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-020 — Durable idempotency store. The in-memory replay cache is bounded and thread-safe but does not survive restart or coordinate multiple controller replicas.

**Current status:** Partial  
**Primary workstream:** State Config  
**Checklist coverage:** C025, C057-C058

### Objective

Make idempotency durable across restarts and controller replicas.

### Referenced production requirements

- **INV-34-C025 — Interfaces & Integration:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Legacy CPU expansion path.
- **INV-34-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Legacy CPU expansion path state.
- **INV-34-C058 — Resilience & Failure Handling:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Make idempotency durable across restarts and controller replicas

### Detailed technical checklist

- [ ] Define idempotency key scope and uniqueness: caller/tenant/VM/request semantic tuple as appropriate.
- [ ] Persist request fingerprint, first accepted result, state generation, created/expiry time, and final outcome.
- [ ] Atomically create/check idempotency record with desired-state mutation so duplicate requests cannot double-apply.
- [ ] Reject key reuse with a different target, generation expectation, VM, or principal using a stable conflict error.
- [ ] Define retention/TTL based on maximum retry/replay horizon and document behavior after expiry.
- [ ] Bound storage growth and provide compaction/garbage collection without deleting active/pending operation keys.
- [ ] Test concurrent duplicate submissions to different controller replicas and restart/replay after ambiguous client timeout.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-021 — Distributed ownership/lease mechanism preventing two live controller replicas from reconciling the same VM concurrently.

**Current status:** Missing  
**Primary workstream:** State Config  
**Checklist coverage:** C058

### Objective

Implement distributed per-VM ownership/lease and fencing.

### Referenced production requirements

- **INV-34-C058 — Resilience & Failure Handling:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement distributed per-VM ownership/lease and fencing

### Detailed technical checklist

- [ ] Choose lease semantics with owner ID, fencing token/epoch, expiry, renewal cadence, and maximum clock assumptions.
- [ ] Require a current fencing token for adapter side effects and durable state transitions.
- [ ] Prevent a paused or partitioned old controller from acting after its lease has been superseded.
- [ ] Define lease handoff/adoption of pending operations without issuing duplicate hot-plug.
- [ ] Handle lease-store unavailability by stopping new side effects before lease validity becomes uncertain.
- [ ] Expose lease owner, age, renewal errors, and fence token in diagnostics without leaking secrets.
- [ ] Run split-brain tests with two replicas, clock skew, long GC/pause, network partition, and recovery.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-022 — Backend retry reconciler with bounded exponential backoff, jitter, retry budget and retryability policy.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C025, C053, C056-C057

### Objective

Implement a backend retry reconciler with safe bounded exponential backoff and jitter.

### Referenced production requirements

- **INV-34-C025 — Interfaces & Integration:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Legacy CPU expansion path.
- **INV-34-C053 — Resilience & Failure Handling:** Implement bounded retry with backoff and jitter only where operations are safe to retry.
- **INV-34-C056 — Resilience & Failure Handling:** Provide degraded operation when noncritical dependencies are unavailable.
- **INV-34-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Legacy CPU expansion path state.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement a backend retry reconciler with safe bounded exponential backoff and jitter

### Detailed technical checklist

- [ ] Run reconciliation from durable desired/observed state rather than from transient request threads.
- [ ] Classify retryability by normalized adapter/observer error code and unknown-outcome semantics.
- [ ] Use exponential backoff with full/equal jitter, minimum/maximum delay, maximum attempts/time budget, and per-VM serialization.
- [ ] Re-check authorization/policy/capacity conditions that are required at retry time without invalidating already-accepted safety semantics.
- [ ] Re-observe current backend state before replaying an ambiguous operation to avoid duplicate CPU additions.
- [ ] Persist next-attempt time, attempt count, last error, and operation/fencing metadata.
- [ ] Route exhausted retries to explicit stalled/quarantined state and alert an operator.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-023 — Circuit breaker / admission and load-shedding layer for overloaded or unhealthy hypervisor/control-plane dependencies.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C054, C067

### Objective

Add admission control, circuit breaking, and load shedding for unhealthy dependencies and overload.

### Referenced production requirements

- **INV-34-C054 — Resilience & Failure Handling:** Implement admission control, load shedding, or circuit breaking to prevent Legacy CPU expansion path failure cascades.
- **INV-34-C067 — Performance & Resource Efficiency:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Add admission control, circuit breaking, and load shedding for unhealthy dependencies and overload

### Detailed technical checklist

- [ ] Define per-dependency circuit states/thresholds for state store, authorization, hypervisor adapter, and observation services.
- [ ] Use bounded per-priority queues and reject excess work with retry-after guidance rather than unbounded memory growth.
- [ ] Protect status/health/emergency-disable traffic from being starved by expansion requests.
- [ ] Gate new expansions when dependency error/latency exceeds thresholds while preserving reconciliation of already accepted state where safe.
- [ ] Use half-open probes and hysteresis to avoid rapid circuit flapping.
- [ ] Expose admission/circuit decisions with reason, dependency, threshold, and configuration version.
- [ ] Test overload waves, dependency brownouts, and recovery without request storms.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-024 — Failover semantics and implementation for controller/backend loss without violating VM ownership or duplicating hot-plug actions.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C055, C058, C089

### Objective

Define and implement controller/backend failover without duplicate or conflicting hot-plug.

### Referenced production requirements

- **INV-34-C055 — Resilience & Failure Handling:** Define failover behavior without violating isolation, residency, or consistency requirements.
- **INV-34-C058 — Resilience & Failure Handling:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.
- **INV-34-C089 — Testing & Certification:** Create disaster, partition, reconnect, and degraded-control-plane tests.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Define and implement controller/backend failover without duplicate or conflicting hot-plug

### Detailed technical checklist

- [ ] Define failover source of truth: durable state plus lease/fencing plus live observation.
- [ ] On takeover, reconstruct every pending VM and observe backend state before issuing any new side effect.
- [ ] Adopt or supersede in-flight adapter operations using operation IDs/fencing rather than blindly retrying.
- [ ] Guarantee at-most-one active reconciler per VM even during controller failover.
- [ ] Define backend failover behavior if multiple hypervisor endpoints/managers can control the same VM.
- [ ] Preserve tenant/site/residency constraints when choosing alternate controllers/backends.
- [ ] Certify failover during request acceptance, adapter dispatch, partial guest online, and final state commit.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-025 — Dependency-loss degraded mode. The desired/observed model can represent non-convergence, but dependency health, retry scheduling and operator state are not implemented.

**Current status:** Partial  
**Primary workstream:** Resilience  
**Checklist coverage:** C048, C052, C056, C071

### Objective

Turn dependency loss into explicit degraded operation with controlled recovery.

### Referenced production requirements

- **INV-34-C048 — Security, Trust & Isolation:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.
- **INV-34-C052 — Resilience & Failure Handling:** Define automated health and stall detection thresholds for Legacy CPU expansion path.
- **INV-34-C056 — Resilience & Failure Handling:** Provide degraded operation when noncritical dependencies are unavailable.
- **INV-34-C071 — Observability & Explainability:** Expose Legacy CPU expansion path health, readiness, version, configuration, dependency status, and active capability set.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Turn dependency loss into explicit degraded operation with controlled recovery

### Detailed technical checklist

- [ ] Define required vs optional dependencies and the allowed service mode for each dependency outage.
- [ ] Keep desired/observed divergence visible when adapter or observer is unavailable; never mark converged from absence of evidence.
- [ ] Stop accepting new expansions if authoritative capacity, authorization, identity, or durable-state guarantees are unavailable.
- [ ] Allow safe read/status or pending reconciliation where policy explicitly permits it.
- [ ] Persist degraded reason, first/last failure time, retry schedule, and operator action required.
- [ ] Add readiness states that differentiate process up, read-only degraded, reconcile-only, and fully ready.
- [ ] Test dependency recovery and ensure queued/retried work ramps up without thundering herd.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-026 — Persistent crash/restart/replay implementation reconstructing pending expansions safely after process or node failure.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C057, C095

### Objective

Implement crash/restart replay that reconstructs pending work safely.

### Referenced production requirements

- **INV-34-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Legacy CPU expansion path state.
- **INV-34-C095 — Operations, Release & Governance:** Provide backup, restore, migration, or reconstruction procedures for Legacy CPU expansion path state where applicable.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement crash/restart replay that reconstructs pending work safely

### Detailed technical checklist

- [ ] Persist enough intent and operation metadata before side effects to recover after process/node failure.
- [ ] At startup, scan owned/adoptable pending records and compare durable state with live hypervisor/guest observation.
- [ ] For ambiguous previous actions, observe first and only retry when duplicate execution is proven safe.
- [ ] Use lease/fencing before any replayed side effect.
- [ ] Define handling of corrupted, incomplete, or schema-old records: migrate, quarantine, or fail startup.
- [ ] Bound startup replay concurrency so mass restart cannot overload hypervisors.
- [ ] Inject crashes before/after each durable write and adapter call to certify exactly the documented recovery semantics.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-027 — Quarantine/freeze control surface. The local `expansion_enabled` flag exists, but no authenticated fleet/operator endpoint or policy distribution mechanism exists.

**Current status:** Partial  
**Primary workstream:** Resilience  
**Checklist coverage:** C059, C092

### Objective

Provide an authenticated fleet/operator quarantine, freeze, and emergency-disable control surface.

### Referenced production requirements

- **INV-34-C059 — Resilience & Failure Handling:** Provide quarantine, freeze, disable, or isolation controls for unsafe Legacy CPU expansion path behavior.
- **INV-34-C092 — Operations, Release & Governance:** Define canary, staged rollout, rollback, and emergency-disable procedures for Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Provide an authenticated fleet/operator quarantine, freeze, and emergency-disable control surface

### Detailed technical checklist

- [ ] Separate global, site, tenant, host, and VM freeze scopes and define precedence.
- [ ] Use strong authorization and break-glass controls for fleet/global actions.
- [ ] Define whether freeze blocks only new requests or also automatic retries/reconciliation; make modes explicit.
- [ ] Do not hot-unplug already online CPUs as a quarantine action.
- [ ] Require reason, ticket/incident ID, actor, expiry/review time, and audit event for overrides.
- [ ] Propagate disable policy to all controller replicas with versioned atomic configuration.
- [ ] Provide status/explain output showing effective freeze source and affected pending operations.
- [ ] Test freeze during in-flight adapter calls and verify safe completion/adoption behavior.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-028 — Host/guest health and stall detector with explicit thresholds for pending expansions and partial hot-plug convergence.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C052, C071, C080

### Objective

Detect stalled or unhealthy hot-plug convergence with explicit thresholds.

### Referenced production requirements

- **INV-34-C052 — Resilience & Failure Handling:** Define automated health and stall detection thresholds for Legacy CPU expansion path.
- **INV-34-C071 — Observability & Explainability:** Expose Legacy CPU expansion path health, readiness, version, configuration, dependency status, and active capability set.
- **INV-34-C080 — Observability & Explainability:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Detect stalled or unhealthy hot-plug convergence with explicit thresholds

### Detailed technical checklist

- [ ] Define stall clocks separately for adapter acknowledgement, CPU presentation, guest online progress, and total convergence.
- [ ] Use per-environment thresholds derived from measured distributions rather than arbitrary constants.
- [ ] Detect zero progress, partial progress, stale observation source, repeated retry, and capacity-change blockage.
- [ ] Classify stall reason and attach last successful stage, last observation, last adapter result, and dependency health.
- [ ] Transition stalled work to retry, degraded, or quarantine according to policy without fabricating failure completion.
- [ ] Emit metrics/alerts for pending age and pending-vCPU backlog with cardinality-safe aggregation.
- [ ] Add tests for slow-but-valid guests to avoid false positives and for permanently stuck guests to ensure timely detection.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-029 — Network/control-plane partition semantics and tests for request submission, state-store access, adapter calls and observation delivery.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C018, C051, C055-C057, C089

### Objective

Specify and certify network/control-plane partition behavior for every dependency path.

### Referenced production requirements

- **INV-34-C018 — Requirements & Semantics:** Define behavior when network connectivity is intermittent or absent.
- **INV-34-C051 — Resilience & Failure Handling:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Legacy CPU expansion path.
- **INV-34-C055 — Resilience & Failure Handling:** Define failover behavior without violating isolation, residency, or consistency requirements.
- **INV-34-C056 — Resilience & Failure Handling:** Provide degraded operation when noncritical dependencies are unavailable.
- **INV-34-C057 — Resilience & Failure Handling:** Define crash-consistency, restart, resume, or replay semantics for mutable Legacy CPU expansion path state.
- **INV-34-C089 — Testing & Certification:** Create disaster, partition, reconnect, and degraded-control-plane tests.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Specify and certify network/control-plane partition behavior for every dependency path

### Detailed technical checklist

- [ ] Enumerate partitions between client↔API, controller↔state store, controller↔auth/policy, controller↔hypervisor, observer↔controller/store, and replica↔replica.
- [ ] Define safe action for one-way, two-way, partial, and high-latency partitions.
- [ ] Use fencing/leases so isolated controllers lose mutation authority before stale side effects are possible.
- [ ] Define client semantics for unknown request outcome after network timeout and require idempotent retry.
- [ ] Define buffering or dropping behavior for observations during disconnect and how freshness is established on reconnect.
- [ ] On reconnect, reconcile from durable intent plus live observation before draining backlog.
- [ ] Automate partition injection and validate no capacity/security invariants are violated.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-030 — Precedence engine for conflicts among capacity, security, residency, SLO and cost constraints.

**Current status:** Missing  
**Primary workstream:** Security  
**Checklist coverage:** C019

### Objective

Implement deterministic precedence among security, residency, capacity, SLO, and cost constraints.

### Referenced production requirements

- **INV-34-C019 — Requirements & Semantics:** Define precedence rules when Legacy CPU expansion path requirements conflict with security, residency, SLO, or cost constraints.

### Required artifacts / deliverables

- [ ] Threat/control design.
- [ ] Enforcement implementation/policy.
- [ ] Security tests and audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement deterministic precedence among security, residency, capacity, SLO, and cost constraints

### Detailed technical checklist

- [ ] Define an ordered decision model where security/isolation and hard physical capacity cannot be overridden by optimization goals.
- [ ] Distinguish hard constraints, soft preferences, emergency overrides, and informational signals.
- [ ] Provide stable reason codes identifying the winning constraint and all material rejected alternatives.
- [ ] Version precedence policy and attach policy version/hash to each decision.
- [ ] Require explicit break-glass capability for any allowed override and prevent overrides of non-overridable safety invariants.
- [ ] Add table-driven tests for every pairwise/multi-constraint conflict, including contradictory policy inputs.
- [ ] Expose operator explain output without leaking other tenants’ quota or topology details.
- [ ] Document assets, principals, trust boundaries, abuse cases, attacker capabilities, and explicit security invariants for the component.
- [ ] Use least-privilege identities and capabilities; prohibit ambient filesystem, network, hypervisor, secret, or cross-tenant authority.
- [ ] Fail closed when identity, authorization, policy, key, attestation, provenance, or trusted-time decisions cannot be established.
- [ ] Define secret/key lifecycle requirements including source, rotation, revocation, memory handling, redaction, and incident response.
- [ ] Generate immutable/tamper-evident audit records for security-relevant state changes and administrative overrides.
- [ ] Add abuse-rate limits and resource bounds that prevent resource-exhaustion attacks from bypassing VM/host capacity safeguards.
- [ ] Derive adversarial tests from the threat model and run them automatically in CI or the certification environment.
- [ ] Require security review evidence and explicit residual-risk/exception records before production enablement.

### Verification and negative-test checklist

- [ ] Run unauthorized, cross-tenant, replay, stale, forged identity/data, exhaustion, and dependency-unavailable cases.
- [ ] Verify all deny/fail-closed paths generate appropriate audit evidence without secret leakage.
- [ ] Have an independent security reviewer verify least privilege and residual-risk disposition.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-031 — Credential/secret integration policy for real adapters, including secret source, rotation and diagnostic redaction.

**Current status:** Missing  
**Primary workstream:** Security  
**Checklist coverage:** C039, C047-C048

### Objective

Integrate real adapter credentials with managed secret lifecycle and diagnostic redaction.

### Referenced production requirements

- **INV-34-C039 — Implementation & Configuration:** Keep credentials and secret material out of ordinary Legacy CPU expansion path configuration and diagnostics.
- **INV-34-C047 — Security, Trust & Isolation:** Encrypt sensitive Legacy CPU expansion path data in transit and at rest with managed key rotation.
- **INV-34-C048 — Security, Trust & Isolation:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

### Required artifacts / deliverables

- [ ] Threat/control design.
- [ ] Enforcement implementation/policy.
- [ ] Security tests and audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Integrate real adapter credentials with managed secret lifecycle and diagnostic redaction

### Detailed technical checklist

- [ ] Select approved secret source/KMS/workload identity mechanism and prohibit plaintext secrets in repository/config/logs.
- [ ] Use short-lived or dynamically issued credentials where the hypervisor/control plane supports them.
- [ ] Grant only the exact hypervisor operations and VM scopes required for CPU hot-add/status.
- [ ] Define rotation, overlap, revocation, bootstrap, and emergency credential replacement procedures.
- [ ] Keep secrets out of exception messages, traces, metrics labels, core dumps, and support bundles.
- [ ] Define memory lifetime/zeroization expectations where practical and avoid serializing credentials into durable state.
- [ ] Add automated secret scanning and tests that inject recognizable canary secrets then verify telemetry redaction.
- [ ] Document assets, principals, trust boundaries, abuse cases, attacker capabilities, and explicit security invariants for the component.
- [ ] Use least-privilege identities and capabilities; prohibit ambient filesystem, network, hypervisor, secret, or cross-tenant authority.
- [ ] Fail closed when identity, authorization, policy, key, attestation, provenance, or trusted-time decisions cannot be established.
- [ ] Define secret/key lifecycle requirements including source, rotation, revocation, memory handling, redaction, and incident response.
- [ ] Generate immutable/tamper-evident audit records for security-relevant state changes and administrative overrides.
- [ ] Add abuse-rate limits and resource bounds that prevent resource-exhaustion attacks from bypassing VM/host capacity safeguards.
- [ ] Derive adversarial tests from the threat model and run them automatically in CI or the certification environment.
- [ ] Require security review evidence and explicit residual-risk/exception records before production enablement.

### Verification and negative-test checklist

- [ ] Run unauthorized, cross-tenant, replay, stale, forged identity/data, exhaustion, and dependency-unavailable cases.
- [ ] Verify all deny/fail-closed paths generate appropriate audit evidence without secret leakage.
- [ ] Have an independent security reviewer verify least privilege and residual-risk disposition.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-032 — Artifact/dependency signature, digest and provenance verification plus approved-version policy for executable adapters/framework dependencies.

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C045

### Objective

Verify signatures, digests, provenance, and approved versions for executable dependencies/adapters.

### Referenced production requirements

- **INV-34-C045 — Security, Trust & Isolation:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Verify signatures, digests, provenance, and approved versions for executable dependencies/adapters

### Detailed technical checklist

- [ ] Define approved artifact repositories/registries and trust roots.
- [ ] Require immutable digest references for adapter images/packages and critical framework dependencies.
- [ ] Verify signature/attestation before build promotion and again before deployment/activation.
- [ ] Bind provenance to source revision, builder identity, build workflow, dependency lock, and artifact digest.
- [ ] Reject unsigned, mismatched, expired/revoked, or policy-disallowed artifacts fail closed.
- [ ] Maintain allow/deny policy for approved versions and emergency revocation.
- [ ] Add negative tests using modified artifacts and forged/untrusted attestations.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-033 — SBOM and supply-chain attestation artifacts for release packages and dependencies.

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C041, C045, C094, C100

### Objective

Generate release SBOMs and supply-chain attestations covering the complete deployable graph.

### Referenced production requirements

- **INV-34-C041 — Security, Trust & Isolation:** Threat-model Legacy CPU expansion path against malicious tenants, compromised workloads, hostile inputs, supply-chain compromise, and control-plane abuse.
- **INV-34-C045 — Security, Trust & Isolation:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Legacy CPU expansion path.
- **INV-34-C094 — Operations, Release & Governance:** Define patching, vulnerability response, and end-of-life SLAs for Legacy CPU expansion path.
- **INV-34-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Generate release SBOMs and supply-chain attestations covering the complete deployable graph

### Detailed technical checklist

- [ ] Produce SPDX or CycloneDX SBOM for source package, runtime image/package, adapters, `pk_core`, and transitive dependencies.
- [ ] Include package name/version, supplier, license, hashes, dependency relationships, and known build-time/runtime distinction.
- [ ] Generate provenance/attestation using a recognized in-toto/SLSA-compatible structure or equivalent.
- [ ] Sign SBOM and attestations and publish them beside release checksums.
- [ ] Validate SBOM completeness against the actual built artifact/filesystem/package metadata.
- [ ] Feed SBOM into vulnerability monitoring and define response linkage to component 64.
- [ ] Archive SBOM/attestation for every released version, including withdrawn releases.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-034 — Tamper-evident security audit event pipeline for expansion request, authorization, acceptance, adapter action, observation, disable and override events.

**Current status:** Missing  
**Primary workstream:** Security  
**Checklist coverage:** C049, C073, C078

### Objective

Implement a tamper-evident security audit event pipeline for all privileged expansion actions.

### Referenced production requirements

- **INV-34-C049 — Security, Trust & Isolation:** Emit tamper-evident audit events for security-sensitive Legacy CPU expansion path operations.
- **INV-34-C073 — Observability & Explainability:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.
- **INV-34-C078 — Observability & Explainability:** Correlate Legacy CPU expansion path events with application release lineage and the live infrastructure graph.

### Required artifacts / deliverables

- [ ] Threat/control design.
- [ ] Enforcement implementation/policy.
- [ ] Security tests and audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement a tamper-evident security audit event pipeline for all privileged expansion actions

### Detailed technical checklist

- [ ] Define event schema for request, authn, authz, desired-state acceptance, adapter dispatch/result, observation, convergence, freeze/disable, override, config change, and rollback.
- [ ] Include stable event ID, actor/principal, tenant/VM, request/operation IDs, generation, policy/config/release versions, timestamp source, outcome, and reason code.
- [ ] Use append-only/WORM or cryptographically chained/externally protected storage appropriate to the threat model.
- [ ] Prevent service identities from deleting or rewriting their own security audit history.
- [ ] Define clock synchronization/trusted-time assumptions and represent uncertainty if trusted time is unavailable.
- [ ] Redact credentials and minimize sensitive tenant payload while retaining investigation value.
- [ ] Create integrity-verification tooling and alert on missing sequence/chaining or ingestion failure.
- [ ] Document assets, principals, trust boundaries, abuse cases, attacker capabilities, and explicit security invariants for the component.
- [ ] Use least-privilege identities and capabilities; prohibit ambient filesystem, network, hypervisor, secret, or cross-tenant authority.
- [ ] Fail closed when identity, authorization, policy, key, attestation, provenance, or trusted-time decisions cannot be established.
- [ ] Define secret/key lifecycle requirements including source, rotation, revocation, memory handling, redaction, and incident response.
- [ ] Generate immutable/tamper-evident audit records for security-relevant state changes and administrative overrides.
- [ ] Add abuse-rate limits and resource bounds that prevent resource-exhaustion attacks from bypassing VM/host capacity safeguards.
- [ ] Derive adversarial tests from the threat model and run them automatically in CI or the certification environment.
- [ ] Require security review evidence and explicit residual-risk/exception records before production enablement.

### Verification and negative-test checklist

- [ ] Run unauthorized, cross-tenant, replay, stale, forged identity/data, exhaustion, and dependency-unavailable cases.
- [ ] Verify all deny/fail-closed paths generate appropriate audit evidence without secret leakage.
- [ ] Have an independent security reviewer verify least privilege and residual-risk disposition.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-035 — Adversarial security test suite for privilege escalation, spoofing, replay across restarts, resource exhaustion, hostile transport payloads and adapter abuse.

**Current status:** Missing  
**Primary workstream:** Security  
**Checklist coverage:** C050, C087

### Objective

Create adversarial security tests derived from the INV-34 threat model.

### Referenced production requirements

- **INV-34-C050 — Security, Trust & Isolation:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.
- **INV-34-C087 — Testing & Certification:** Create security tests derived directly from the Legacy CPU expansion path threat model.

### Required artifacts / deliverables

- [ ] Threat/control design.
- [ ] Enforcement implementation/policy.
- [ ] Security tests and audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Create adversarial security tests derived from the INV-34 threat model

### Detailed technical checklist

- [ ] Test cross-tenant VM expansion attempts, confused-deputy requests, privilege escalation, break-glass misuse, and unauthorized freeze/resume.
- [ ] Test replay across process restart and replica failover using reused idempotency keys and stale generations.
- [ ] Test spoofed guest observations, forged adapter responses, wrong-VM operation IDs, and stale signed data.
- [ ] Test oversized/hostile transport payloads, identifier abuse, parser edge cases, request floods, and quota bypass attempts.
- [ ] Test secret exposure through logs, traces, metrics, exception bodies, crash artifacts, and support bundles.
- [ ] Test artifact/dependency tampering and untrusted provenance.
- [ ] Test policy/identity/key/time-service outage and verify fail-closed behavior for new expansions.
- [ ] Require security regression cases for every discovered vulnerability before closure.
- [ ] Document assets, principals, trust boundaries, abuse cases, attacker capabilities, and explicit security invariants for the component.
- [ ] Use least-privilege identities and capabilities; prohibit ambient filesystem, network, hypervisor, secret, or cross-tenant authority.
- [ ] Fail closed when identity, authorization, policy, key, attestation, provenance, or trusted-time decisions cannot be established.
- [ ] Define secret/key lifecycle requirements including source, rotation, revocation, memory handling, redaction, and incident response.
- [ ] Generate immutable/tamper-evident audit records for security-relevant state changes and administrative overrides.
- [ ] Add abuse-rate limits and resource bounds that prevent resource-exhaustion attacks from bypassing VM/host capacity safeguards.
- [ ] Derive adversarial tests from the threat model and run them automatically in CI or the certification environment.
- [ ] Require security review evidence and explicit residual-risk/exception records before production enablement.

### Verification and negative-test checklist

- [ ] Run unauthorized, cross-tenant, replay, stale, forged identity/data, exhaustion, and dependency-unavailable cases.
- [ ] Verify all deny/fail-closed paths generate appropriate audit evidence without secret leakage.
- [ ] Have an independent security reviewer verify least privilege and residual-risk disposition.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-036 — Fuzz/property-based tests for public schemas, transport handlers and state transition inputs.

**Current status:** Missing  
**Primary workstream:** Testing  
**Checklist coverage:** C050, C085

### Objective

Fuzz and property-test schemas, transport handlers, and state transitions.

### Referenced production requirements

- **INV-34-C050 — Security, Trust & Isolation:** Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.
- **INV-34-C085 — Testing & Certification:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Test plan and deterministic fixtures.
- [ ] Automated executable test suite.
- [ ] Machine-readable results and retained reproduction metadata.
- [ ] Component-specific design/implementation artifact demonstrating: Fuzz and property-test schemas, transport handlers, and state transitions

### Detailed technical checklist

- [ ] Build generators for valid/invalid request/result/status payloads, identifiers, vCPU bounds, generation values, and optional fields.
- [ ] Assert invariants: desired>=observed, no shrink, desired<=configured max, accepted target<=approved host capacity, generation monotonicity, and deterministic idempotent replay.
- [ ] Fuzz decoder/framing/content-type/version negotiation at the real transport boundary.
- [ ] Fuzz state-store serialization/migration and adapter error normalization.
- [ ] Use stateful/property-based sequences covering request→retry→observation→restart→replay.
- [ ] Minimize and persist failing corpus cases as regression fixtures.
- [ ] Run sanitizers/runtime hardening available to the implementation language and set a minimum fuzz time/coverage budget for CI/nightly jobs.
- [ ] Define a versioned test plan with explicit scope, prerequisites, topology, fixtures, deterministic seeds, and pass/fail criteria.
- [ ] Test both positive and negative behavior at the public boundary and assert durable state plus backend/guest truth, not only return codes.
- [ ] Cover boundary values, malformed inputs, stale generations, duplicate/replayed requests, partial progress, and dependency failures.
- [ ] Make tests isolated and reproducible; clean up VMs/state/leases/fixtures even after failure or interruption.
- [ ] Record environment, dependency, hypervisor/guest, schema, configuration, seed, and artifact versions with every test run.
- [ ] Persist failing seeds/corpora/traces and convert every discovered defect into a permanent regression case.
- [ ] Run required suites automatically in CI/certification and fail closed when a mandatory suite is skipped or unavailable.
- [ ] Publish machine-readable results and link them into the RTM and formal production exit gate.

### Verification and negative-test checklist

- [ ] Run the suite repeatedly with deterministic seeds plus randomized/stress variants and archive failing seeds/corpora.
- [ ] Validate assertions against durable state and real/emulated backend observations, not solely API return codes.
- [ ] Ensure every previously discovered defect receives a permanent regression test before closure.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-037 — Concurrency/race certification across processes/replicas. Thread-level duplicate-request behavior is tested; distributed races are not.

**Current status:** Partial  
**Primary workstream:** Testing  
**Checklist coverage:** C086, C058

### Objective

Certify concurrency and race behavior across processes and controller replicas.

### Referenced production requirements

- **INV-34-C058 — Resilience & Failure Handling:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.
- **INV-34-C086 — Testing & Certification:** Create concurrency and race-condition tests for shared/distributed Legacy CPU expansion path state.

### Required artifacts / deliverables

- [ ] Test plan and deterministic fixtures.
- [ ] Automated executable test suite.
- [ ] Machine-readable results and retained reproduction metadata.
- [ ] Component-specific design/implementation artifact demonstrating: Certify concurrency and race behavior across processes and controller replicas

### Detailed technical checklist

- [ ] Test same VM/same idempotency key racing across N replicas.
- [ ] Test same VM/different targets with equal/stale expected generations and verify only valid serialized transitions commit.
- [ ] Test lease transfer while a controller is paused between durable state commit and adapter action.
- [ ] Test simultaneous observation updates and desired-state changes without lost updates.
- [ ] Test quota admission races for the last host/site/tenant capacity unit.
- [ ] Test replica restart and state-store failover during contention.
- [ ] Use deterministic schedulers/fault hooks where possible and supplement with long randomized stress runs.
- [ ] Prove invariants from final durable records and actual hypervisor/guest state, not only API responses.
- [ ] Define a versioned test plan with explicit scope, prerequisites, topology, fixtures, deterministic seeds, and pass/fail criteria.
- [ ] Test both positive and negative behavior at the public boundary and assert durable state plus backend/guest truth, not only return codes.
- [ ] Cover boundary values, malformed inputs, stale generations, duplicate/replayed requests, partial progress, and dependency failures.
- [ ] Make tests isolated and reproducible; clean up VMs/state/leases/fixtures even after failure or interruption.
- [ ] Record environment, dependency, hypervisor/guest, schema, configuration, seed, and artifact versions with every test run.
- [ ] Persist failing seeds/corpora/traces and convert every discovered defect into a permanent regression case.
- [ ] Run required suites automatically in CI/certification and fail closed when a mandatory suite is skipped or unavailable.
- [ ] Publish machine-readable results and link them into the RTM and formal production exit gate.

### Verification and negative-test checklist

- [ ] Run the suite repeatedly with deterministic seeds plus randomized/stress variants and archive failing seeds/corpora.
- [ ] Validate assertions against durable state and real/emulated backend observations, not solely API return codes.
- [ ] Ensure every previously discovered defect receives a permanent regression test before closure.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-038 — Fault-injection suite covering adapter timeouts, partial guest online, hypervisor restart, stale observation, capacity loss, controller crash and recovery.

**Current status:** Missing  
**Primary workstream:** Resilience  
**Checklist coverage:** C051, C060, C089

### Objective

Build deterministic fault injection for all critical hot-plug stages and dependencies.

### Referenced production requirements

- **INV-34-C051 — Resilience & Failure Handling:** Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Legacy CPU expansion path.
- **INV-34-C060 — Resilience & Failure Handling:** Run fault-injection tests proving Legacy CPU expansion path recovery against documented objectives.
- **INV-34-C089 — Testing & Certification:** Create disaster, partition, reconnect, and degraded-control-plane tests.

### Required artifacts / deliverables

- [ ] Failure-mode/recovery specification.
- [ ] Recovery/reconciliation implementation.
- [ ] Fault-injection and disaster evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Build deterministic fault injection for all critical hot-plug stages and dependencies

### Detailed technical checklist

- [ ] Inject adapter connection failure, timeout, throttling, unknown outcome, partial application, and hypervisor restart.
- [ ] Inject guest partial-online, delayed-online, observation loss, stale observation, duplicated observation, and impossible regression.
- [ ] Inject host capacity reduction after acceptance and before/after partial convergence.
- [ ] Crash controller before/after state commit, lease acquisition, adapter dispatch, result persistence, and observation persistence.
- [ ] Inject state-store latency, transaction conflict, temporary unavailability, failover, and stale read where the backend can exhibit it.
- [ ] Inject auth/policy/identity/key/time service outages and recovery.
- [ ] Assert no hot-unplug, no false convergence, no double hot-add, and no stale writer action under every scenario.
- [ ] Create a failure-mode matrix covering timeout, disconnect, partial completion, stale data, dependency restart, controller crash, and operator intervention.
- [ ] Define which operations are retryable and prove retries are idempotent or fenced before enabling automated retry.
- [ ] Bound retries, queues, concurrency, memory, and recovery work; include backoff, jitter, retry budgets, and circuit-opening thresholds.
- [ ] Preserve monotonic hot-add and desired-versus-observed truth during failover, replay, reconnect, and degraded operation.
- [ ] Use generation/lease/fencing mechanisms so stale or duplicate controllers cannot issue conflicting hypervisor actions.
- [ ] Expose explicit degraded, pending, blocked, quarantined, and recovery states rather than fabricating convergence.
- [ ] Provide safe operator controls for freeze, resume, abandon/reconcile, and emergency disable with audit logging.
- [ ] Certify recovery objectives with deterministic fault-injection and disaster/partition scenarios before release.

### Verification and negative-test checklist

- [ ] Inject each documented failure at deterministic points before, during, and after external side effects.
- [ ] Verify bounded resource use, fencing, idempotent recovery, explicit degraded state, and no safety invariant violation.
- [ ] Measure recovery time and backlog drain behavior against approved objectives.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-039 — Integration tests with adjacent layers : capability discovery, authorization, hypervisor adapter, guest observation and durable state.

**Current status:** Missing  
**Primary workstream:** Testing  
**Checklist coverage:** C030, C083

### Objective

Create end-to-end integration tests with capability discovery, authz, state, hypervisor adapter, and guest observation.

### Referenced production requirements

- **INV-34-C030 — Interfaces & Integration:** Create automated integration tests proving Legacy CPU expansion path interoperates with adjacent architectural layers.
- **INV-34-C083 — Testing & Certification:** Create integration tests with every supported adjacent layer and execution tier.

### Required artifacts / deliverables

- [ ] Test plan and deterministic fixtures.
- [ ] Automated executable test suite.
- [ ] Machine-readable results and retained reproduction metadata.
- [ ] Component-specific design/implementation artifact demonstrating: Create end-to-end integration tests with capability discovery, authz, state, hypervisor adapter, and guest observation

### Detailed technical checklist

- [ ] Provision a representative VM with known initial/max vCPU topology and authoritative capability-discovery inputs.
- [ ] Submit an authorized request through the real transport and assert durable desired state before backend convergence.
- [ ] Verify the adapter performs the expected hypervisor action and the guest observer independently confirms online CPUs.
- [ ] Assert final convergence only when observed equals desired; retain timing and operation IDs as evidence.
- [ ] Cover rejection for unsupported hot-plug, insufficient host capacity, quota denial, stale generation, disabled expansion, and unauthorized caller.
- [ ] Cover partial guest online and recovery without duplicate CPU attachment.
- [ ] Run tests for each supported environment/tier and compatibility-matrix row designated production-supported.
- [ ] Define a versioned test plan with explicit scope, prerequisites, topology, fixtures, deterministic seeds, and pass/fail criteria.
- [ ] Test both positive and negative behavior at the public boundary and assert durable state plus backend/guest truth, not only return codes.
- [ ] Cover boundary values, malformed inputs, stale generations, duplicate/replayed requests, partial progress, and dependency failures.
- [ ] Make tests isolated and reproducible; clean up VMs/state/leases/fixtures even after failure or interruption.
- [ ] Record environment, dependency, hypervisor/guest, schema, configuration, seed, and artifact versions with every test run.
- [ ] Persist failing seeds/corpora/traces and convert every discovered defect into a permanent regression case.
- [ ] Run required suites automatically in CI/certification and fail closed when a mandatory suite is skipped or unavailable.
- [ ] Publish machine-readable results and link them into the RTM and formal production exit gate.

### Verification and negative-test checklist

- [ ] Run the suite repeatedly with deterministic seeds plus randomized/stress variants and archive failing seeds/corpora.
- [ ] Validate assertions against durable state and real/emulated backend observations, not solely API return codes.
- [ ] Ensure every previously discovered defect receives a permanent regression test before closure.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-040 — Contract tests against real supported APIs/protocol versions rather than only local Python objects and JSON artifacts.

**Current status:** Missing  
**Primary workstream:** Testing  
**Checklist coverage:** C082-C084

### Objective

Run contract tests against real APIs/protocol versions, not only local Python objects.

### Referenced production requirements

- **INV-34-C082 — Testing & Certification:** Create contract tests for every public Legacy CPU expansion path interface.
- **INV-34-C083 — Testing & Certification:** Create integration tests with every supported adjacent layer and execution tier.
- **INV-34-C084 — Testing & Certification:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Test plan and deterministic fixtures.
- [ ] Automated executable test suite.
- [ ] Machine-readable results and retained reproduction metadata.
- [ ] Component-specific design/implementation artifact demonstrating: Run contract tests against real APIs/protocol versions, not only local Python objects

### Detailed technical checklist

- [ ] Generate or hand-maintain canonical request/result/status fixtures with exact wire encodings.
- [ ] Run consumer/provider contract tests against each supported transport and hypervisor/observer API version.
- [ ] Validate HTTP/RPC status mapping, headers/metadata, deadlines, idempotency keys, correlation, and structured error bodies.
- [ ] Validate unknown/additive fields, enum evolution, malformed payloads, oversized messages, and version negotiation.
- [ ] Run the same suite against N and N-1 peers where supported.
- [ ] Capture API/server version and fixture digest in test evidence.
- [ ] Block release if a supported provider changes behavior without an approved compatibility update.
- [ ] Define a versioned test plan with explicit scope, prerequisites, topology, fixtures, deterministic seeds, and pass/fail criteria.
- [ ] Test both positive and negative behavior at the public boundary and assert durable state plus backend/guest truth, not only return codes.
- [ ] Cover boundary values, malformed inputs, stale generations, duplicate/replayed requests, partial progress, and dependency failures.
- [ ] Make tests isolated and reproducible; clean up VMs/state/leases/fixtures even after failure or interruption.
- [ ] Record environment, dependency, hypervisor/guest, schema, configuration, seed, and artifact versions with every test run.
- [ ] Persist failing seeds/corpora/traces and convert every discovered defect into a permanent regression case.
- [ ] Run required suites automatically in CI/certification and fail closed when a mandatory suite is skipped or unavailable.
- [ ] Publish machine-readable results and link them into the RTM and formal production exit gate.

### Verification and negative-test checklist

- [ ] Run the suite repeatedly with deterministic seeds plus randomized/stress variants and archive failing seeds/corpora.
- [ ] Validate assertions against durable state and real/emulated backend observations, not solely API return codes.
- [ ] Ensure every previously discovered defect receives a permanent regression test before closure.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-041 — Reproducible performance baseline harness for request latency, reconciliation latency, CPU, memory, storage/network overhead and startup.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C061

### Objective

Build a reproducible performance baseline harness for the complete production path.

### Referenced production requirements

- **INV-34-C061 — Performance & Resource Efficiency:** Establish reproducible baselines for Legacy CPU expansion path latency, throughput, startup, CPU, memory, storage, network, and power overhead.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Build a reproducible performance baseline harness for the complete production path

### Detailed technical checklist

- [ ] Measure pure admission decision, authenticated API request, durable state transaction, adapter dispatch, observation processing, and total convergence separately.
- [ ] Parameterize VM count, vCPU delta, controller replicas, request concurrency, hypervisor latency, guest online latency, and state-store latency.
- [ ] Collect service CPU/RSS/allocations, store I/O, RPC bytes, open connections, queue depth, context switches, and startup time.
- [ ] Include cold-start and steady-state runs and clearly separate cache/warm effects.
- [ ] Fingerprint host CPU, OS/kernel, Python/runtime, hypervisor, guest, adapter, state store, and configuration.
- [ ] Emit raw results in machine-readable format plus summarized percentiles.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-042 — Approved p50/p95/p99/worst-case thresholds and release acceptance limits.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C062, C070

### Objective

Define approved p50/p95/p99/max thresholds and release acceptance limits.

### Referenced production requirements

- **INV-34-C062 — Performance & Resource Efficiency:** Define p50, p95, p99, and worst-case performance thresholds for Legacy CPU expansion path.
- **INV-34-C070 — Performance & Resource Efficiency:** Block releases that regress approved Legacy CPU expansion path startup, density, throughput, or tail-latency thresholds.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Define approved p50/p95/p99/max thresholds and release acceptance limits

### Detailed technical checklist

- [ ] Define thresholds per stage: admission, state commit, adapter acknowledgement, observation lag, and total convergence.
- [ ] Define throughput and maximum backlog/in-flight limits for normal and degraded conditions.
- [ ] Define controller CPU/memory overhead budgets at representative VM/fleet scale.
- [ ] Define startup/readiness budget and maximum recovery catch-up time after restart.
- [ ] Define separate SLO versus hard safety timeout thresholds; avoid treating slow convergence as permission to claim success.
- [ ] Set statistically justified regression tolerance and minimum sample size/confidence method.
- [ ] Version threshold policy and require approval for threshold relaxation.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-043 — Steady/burst/overload/scale/recovery performance tests.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C063, C088

### Objective

Exercise steady, burst, overload, scale, and recovery workloads.

### Referenced production requirements

- **INV-34-C063 — Performance & Resource Efficiency:** Measure Legacy CPU expansion path under steady load, burst load, overload, scale-out, scale-in, and recovery.
- **INV-34-C088 — Testing & Certification:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Exercise steady, burst, overload, scale, and recovery workloads

### Detailed technical checklist

- [ ] Define steady-state request rates and fleet size representative of production.
- [ ] Generate burst waves that exceed nominal request rate while staying within bounded queue/admission design.
- [ ] Drive overload beyond configured capacity to verify fast rejection/load shedding rather than collapse.
- [ ] Test scale-out of controller replicas and quantify contention on shared state/leases.
- [ ] Test operational scale-in/failover of controller replicas; CPU hot-unplug itself remains out of scope.
- [ ] Measure recovery after hypervisor/state-store/observer outage with accumulated pending work.
- [ ] Report latency percentiles, backlog, dropped/rejected work, errors, resource saturation, and recovery time for every phase.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-044 — Per-workload/per-tenant overhead measurements for the full production path.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C064

### Objective

Measure full-path overhead per workload and tenant.

### Referenced production requirements

- **INV-34-C064 — Performance & Resource Efficiency:** Measure per-workload and per-tenant overhead introduced by Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Measure full-path overhead per workload and tenant

### Detailed technical checklist

- [ ] Attribute request/control overhead by tenant/workload without exposing cross-tenant sensitive details.
- [ ] Measure incremental controller CPU/memory/store/network cost per active VM, pending expansion, request, and observation.
- [ ] Measure authorization/quota/telemetry overhead added to the hot path.
- [ ] Test small and large tenants to detect fixed-cost and cardinality-driven scaling issues.
- [ ] Validate one noisy tenant cannot materially degrade another beyond approved fairness/SLO budgets.
- [ ] Use the data to set quotas, rate limits, capacity forecasts, and chargeback/showback only if required by product policy.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-045 — Serialization/copy/context-switch/network-hop analysis of the real adapter and state/telemetry path.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C065-C066

### Objective

Analyze serialization, copies, context switches, and network hops in the real path.

### Referenced production requirements

- **INV-34-C065 — Performance & Resource Efficiency:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Legacy CPU expansion path.
- **INV-34-C066 — Performance & Resource Efficiency:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Analyze serialization, copies, context switches, and network hops in the real path

### Detailed technical checklist

- [ ] Draw the complete request-to-convergence sequence with every process/thread hop, RPC, serialization, durable write, and telemetry emission.
- [ ] Measure payload size and serialization/deserialization CPU for each contract.
- [ ] Profile copies/allocations and repeated state reads/writes in admission/reconciliation paths.
- [ ] Measure context switches/syscalls and connection setup/TLS overhead under load.
- [ ] Identify avoidable duplicate polling or duplicated state/telemetry fan-out.
- [ ] Only introduce batching/caching/direct composition when it preserves authorization, freshness, durability, and per-VM ordering semantics.
- [ ] Re-benchmark after each optimization and retain before/after evidence.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-046 — Fleet resource bounds. Local vCPU/replay bounds exist; queue depth, RPC concurrency, worker fan-out and fleet-level memory bounds depend on missing services.

**Current status:** Partial  
**Primary workstream:** Performance  
**Checklist coverage:** C067

### Objective

Bound fleet-level memory, queues, concurrency, worker fan-out, and RPC resources.

### Referenced production requirements

- **INV-34-C067 — Performance & Resource Efficiency:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Bound fleet-level memory, queues, concurrency, worker fan-out, and RPC resources

### Detailed technical checklist

- [ ] Define hard limits for global/per-tenant/per-host/per-VM queued requests and reconciliation work.
- [ ] Define maximum worker/thread/task count, outbound RPC concurrency, open connections, and state-store transactions.
- [ ] Bound in-memory caches including idempotency, compatibility, policy, and observation caches with eviction semantics.
- [ ] Reject/admit work before resource growth becomes unbounded and expose saturation metrics.
- [ ] Protect emergency/read/status traffic with reserved capacity or priority classes.
- [ ] Load test at and above every bound and verify predictable rejection rather than OOM/thread exhaustion.
- [ ] Document sizing formulas and default limits per deployment tier.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-047 — Power and thermal impact characterization on constrained edge nodes during/after CPU hot-add where applicable.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C068

### Objective

Characterize power and thermal impact on constrained edge nodes where CPU hot-add is used.

### Referenced production requirements

- **INV-34-C068 — Performance & Resource Efficiency:** Measure power and thermal impact on constrained edge nodes where relevant.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Characterize power and thermal impact on constrained edge nodes where CPU hot-add is used

### Detailed technical checklist

- [ ] Define applicable edge hardware and thermal/power envelopes; explicitly mark non-edge deployments N/A with rationale.
- [ ] Measure idle and load power before/after hot-add at multiple vCPU deltas and workload profiles.
- [ ] Measure package/system temperature, throttling indicators, frequency changes, fan behavior, and sustained performance.
- [ ] Correlate added vCPUs with host contention and thermal headroom signals used by capacity policy.
- [ ] Define safeguards when thermal/power limits are near exhaustion, including rejection/defer policy if applicable.
- [ ] Run soak tests long enough to reach thermal steady state and document ambient/test conditions.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-048 — Capacity model and saturation predictor beyond direct ceiling checks, including forecastable headroom signals.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C069

### Objective

Create a capacity model and saturation predictor beyond immediate ceiling checks.

### Referenced production requirements

- **INV-34-C069 — Performance & Resource Efficiency:** Define capacity models and saturation signals that predict when Legacy CPU expansion path needs more resources.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Create a capacity model and saturation predictor beyond immediate ceiling checks

### Detailed technical checklist

- [ ] Define capacity inputs including physical/logical CPUs, reserved system capacity, overcommit policy, pinned CPUs, topology/NUMA constraints, pending expansions, and tenant reserves.
- [ ] Distinguish instantaneous available capacity from safe allocatable headroom and forecasted saturation.
- [ ] Account for already accepted-but-not-yet-observed vCPUs so pending work is not double-allocated.
- [ ] Define stale capacity TTL and fail-closed behavior when authoritative capacity is unknown.
- [ ] Expose saturation signals such as allocation ratio, pending commitments, queue age, and forecast time-to-exhaustion.
- [ ] Validate model predictions against load/soak data and tune error bounds.
- [ ] Keep predictive output advisory unless explicitly made a policy input with tested precedence.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-049 — Release performance-regression gate that blocks startup/density/throughput/tail-latency regressions.

**Current status:** Missing  
**Primary workstream:** Performance  
**Checklist coverage:** C070

### Objective

Block releases on approved performance regressions.

### Referenced production requirements

- **INV-34-C070 — Performance & Resource Efficiency:** Block releases that regress approved Legacy CPU expansion path startup, density, throughput, or tail-latency thresholds.

### Required artifacts / deliverables

- [ ] Benchmark methodology and harness.
- [ ] Machine-readable raw results/baseline.
- [ ] Approved thresholds/regression gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Block releases on approved performance regressions

### Detailed technical checklist

- [ ] Run baseline and candidate on comparable pinned environments or use controlled normalization.
- [ ] Compare startup/readiness, admission throughput/latency, reconciliation throughput, convergence overhead, density, CPU, memory, and tail latency.
- [ ] Define per-metric warn/fail thresholds and statistical comparison method.
- [ ] Require an explicit time-bounded waiver with owner/rationale for any permitted regression.
- [ ] Publish machine-readable gate result linked to benchmark raw data and commit/artifact digest.
- [ ] Prevent rerunning only favorable subsets; retain all required benchmark cases for each release candidate.
- [ ] Define representative topology, VM sizes, host sizes, request rates, concurrency, guest-online delays, and dependency latencies for measurement.
- [ ] Use a reproducible benchmark harness with pinned software/hardware metadata, warm-up policy, sample counts, clock source, and noise controls.
- [ ] Measure request-decision latency separately from adapter dispatch, guest-online convergence, and total control-loop completion latency.
- [ ] Collect CPU, memory, allocation, queue, network, storage, context-switch, syscall, and power/thermal signals where applicable.
- [ ] Report p50/p95/p99/max plus throughput, error rate, saturation point, backlog, and recovery time; do not use averages alone.
- [ ] Establish approved thresholds and statistically defensible regression tolerances, including noisy-neighbor and overload cases.
- [ ] Archive raw benchmark inputs/results and environment fingerprints so a release result can be independently reproduced.
- [ ] Block release promotion when required performance/resource limits regress beyond the approved budget.

### Verification and negative-test checklist

- [ ] Run at least three repeatable trials per mandatory scenario or use an approved statistically equivalent methodology.
- [ ] Compare candidate against approved baseline and report percent/absolute change with raw samples retained.
- [ ] Repeat worst regressions under profiling to identify causality before accepting a waiver.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-050 — Production health/readiness/version/configuration/dependency endpoint for the deployed service/adapter.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C071

### Objective

Expose production health/readiness/version/configuration/dependency/capability status.

### Referenced production requirements

- **INV-34-C071 — Observability & Explainability:** Expose Legacy CPU expansion path health, readiness, version, configuration, dependency status, and active capability set.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Expose production health/readiness/version/configuration/dependency/capability status

### Detailed technical checklist

- [ ] Separate liveness from readiness and from safe ability to accept new expansion requests.
- [ ] Report service version/build digest, active config generation/digest, schema versions, adapter version, state-store version, and capability profile.
- [ ] Report dependency health/freshness for authn/authz, capacity discovery, state store, hypervisor adapter, and observer.
- [ ] Report whether expansion is enabled/frozen and the effective scope/reason without leaking sensitive policy data.
- [ ] Include pending/stalled counts and oldest pending age in operator status.
- [ ] Make readiness fail or degrade according to dependency-loss policy; do not return healthy solely because the process event loop runs.
- [ ] Protect detailed endpoint access and keep public probes minimal.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-051 — Metrics exporter implementing request rate/errors, convergence latency, saturation, pending-vCPU backlog and resource use.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C072

### Objective

Implement metrics for rate, errors, convergence, saturation, backlog, and resource use.

### Referenced production requirements

- **INV-34-C072 — Observability & Explainability:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement metrics for rate, errors, convergence, saturation, backlog, and resource use

### Detailed technical checklist

- [ ] Export request counters by outcome/error code without VM/request IDs as metric labels.
- [ ] Export desired-observed pending vCPU aggregate gauges by bounded dimensions such as site/tenant tier, not raw VM IDs unless explicitly controlled.
- [ ] Export histograms for admission latency, adapter latency, observation lag, total convergence, state-store latency, and authz latency.
- [ ] Export queue depth, in-flight reconciliations, retry attempts, circuit state, lease contention, and stalled work.
- [ ] Export process CPU/RSS/GC/runtime and outbound dependency saturation/error metrics.
- [ ] Define histogram buckets from measured data and SLO thresholds.
- [ ] Add automated metric-contract tests for names, units, types, label cardinality, and reset behavior.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-052 — Structured logging pipeline with stable VM/node/tenant/workload/component/operation identifiers and redaction policy.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C073, C075

### Objective

Implement structured logging with stable identifiers and redaction.

### Referenced production requirements

- **INV-34-C073 — Observability & Explainability:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.
- **INV-34-C075 — Observability & Explainability:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement structured logging with stable identifiers and redaction

### Detailed technical checklist

- [ ] Define a versioned log event taxonomy for request lifecycle, state transition, adapter action, observation, retry, stall, freeze, config, and security events.
- [ ] Include tenant-safe identifiers: component, node, VM/workload stable opaque ID, request ID, operation ID, generation, release/config version, and trace ID.
- [ ] Do not log raw credentials, authorization tokens, secrets, full guest payloads, or unnecessary tenant data.
- [ ] Use deterministic redaction/tokenization rules and mark redacted fields explicitly where useful.
- [ ] Ensure log severity maps to operational action and avoid error-level logging for expected policy rejections.
- [ ] Add schema validation tests and canary-secret leakage tests.
- [ ] Define rotation/backpressure behavior so logging failure cannot block or exhaust the control path.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-053 — Distributed trace propagation through request transport, state store, hypervisor adapter and observation path.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C074

### Objective

Propagate distributed trace context across every request and reconciliation boundary.

### Referenced production requirements

- **INV-34-C074 — Observability & Explainability:** Propagate trace context across all relevant Legacy CPU expansion path boundaries.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Propagate distributed trace context across every request and reconciliation boundary

### Detailed technical checklist

- [ ] Choose trace context standard and define propagation through external transport, internal queue, state operations, authz, adapter, observer, and audit pipeline.
- [ ] Create spans for admission, durable transaction, lease acquire/renew, adapter action, observation wait/process, and convergence.
- [ ] Attach bounded attributes such as outcome/error code, generation, adapter type/version, and site; avoid high-cardinality secrets/tenant payloads.
- [ ] Link asynchronous observation/reconciliation spans to the originating request using trace links when parent-child timing is inappropriate.
- [ ] Define sampling that retains errors/slow/stalled/security events while controlling cost.
- [ ] Test trace continuity across process restart and queued asynchronous work where correlation metadata is persisted.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-054 — Safe high-cardinality diagnostic channel with tenant/secret leakage controls.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C075

### Objective

Provide a safe high-cardinality diagnostic channel without leaking tenant/secret data.

### Referenced production requirements

- **INV-34-C075 — Observability & Explainability:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Provide a safe high-cardinality diagnostic channel without leaking tenant/secret data

### Detailed technical checklist

- [ ] Separate high-cardinality diagnostic events from low-cardinality metrics.
- [ ] Require authenticated/authorized operator access and tenant-scoped filtering.
- [ ] Use opaque stable IDs instead of names/emails/raw tenant metadata where possible.
- [ ] Apply field-level allowlists/redaction and prevent secrets from entering free-form diagnostic text.
- [ ] Bound event rate/size/retention and protect the service when the diagnostic sink is slow or unavailable.
- [ ] Provide targeted per-VM/request debugging with explicit short-lived enablement rather than global verbose logging.
- [ ] Audit access to sensitive diagnostic data and test cross-tenant isolation.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-055 — Decision explanation surface. Structured errors/state provide local reasons, but no complete operator-facing explain API links inputs, policy, topology and constraints.

**Current status:** Partial  
**Primary workstream:** Observability  
**Checklist coverage:** C076-C077

### Objective

Expose a complete operator-facing explanation for every decision and blocked convergence.

### Referenced production requirements

- **INV-34-C076 — Observability & Explainability:** Record the reason for every automated decision made by Legacy CPU expansion path.
- **INV-34-C077 — Observability & Explainability:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Expose a complete operator-facing explanation for every decision and blocked convergence

### Detailed technical checklist

- [ ] Define an explain response containing input state snapshot, desired/observed/max/capacity, capabilities, authz/quota/policy decisions, config/policy versions, topology facts, and final reason codes.
- [ ] Distinguish request rejection from accepted-but-pending and accepted-but-stalled states.
- [ ] Explain which constraint won when multiple constraints were evaluated without exposing another tenant’s confidential details.
- [ ] Include freshness/source metadata for capacity and observation facts.
- [ ] Link to relevant audit/log/trace IDs and adapter operation ID.
- [ ] Make explain generation read-only and side-effect free.
- [ ] Add golden tests ensuring each machine-readable error/state has a stable human/operator explanation.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-056 — Release-lineage and infrastructure-graph correlation for expansion events.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C078

### Objective

Correlate expansion events with application release lineage and the live infrastructure graph.

### Referenced production requirements

- **INV-34-C078 — Observability & Explainability:** Correlate Legacy CPU expansion path events with application release lineage and the live infrastructure graph.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Correlate expansion events with application release lineage and the live infrastructure graph

### Detailed technical checklist

- [ ] Capture workload/application release ID, deployment revision, VM instance ID, host/node ID, site, and controller/adapter release on each event where available.
- [ ] Define integration with the authoritative infrastructure/service graph rather than creating a competing topology database.
- [ ] Record topology snapshot/version or resolvable graph reference used for the decision.
- [ ] Handle VM migration/host changes while an expansion is pending and preserve event lineage.
- [ ] Provide queries from incident/release → affected expansion events and from expansion event → release/topology context.
- [ ] Apply access controls so graph correlation does not leak other tenants’ infrastructure.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-057 — Telemetry retention, sampling, privacy and export policy.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C079

### Objective

Define telemetry retention, sampling, privacy, export, and deletion policy.

### Referenced production requirements

- **INV-34-C079 — Observability & Explainability:** Define telemetry retention, sampling, privacy, and export policy.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Define telemetry retention, sampling, privacy, export, and deletion policy

### Detailed technical checklist

- [ ] Classify metrics/logs/traces/audit events by sensitivity and regulatory/tenant impact.
- [ ] Set retention windows by signal type and investigation/compliance need; security audit retention may differ from debug traces.
- [ ] Define sampling rules that preserve errors, security denials, stalls, and release-gate evidence.
- [ ] Define allowed export destinations, encryption in transit/at rest, regional/residency restrictions, and processor agreements where applicable.
- [ ] Define tenant deletion/anonymization behavior without corrupting required immutable security records.
- [ ] Control high-cardinality cost with budgets and rate limits rather than dropping critical audit evidence.
- [ ] Document access roles and periodically review telemetry permissions.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-058 — Dashboards and alerts distinguishing normal load, capacity rejection, dependency failure, stalled convergence, attack and software defect.

**Current status:** Missing  
**Primary workstream:** Observability  
**Checklist coverage:** C080

### Objective

Create actionable dashboards and alerts that distinguish load, capacity, dependency, security, and software failures.

### Referenced production requirements

- **INV-34-C080 — Observability & Explainability:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

### Required artifacts / deliverables

- [ ] Telemetry schema/semantic conventions.
- [ ] Exporter/endpoint/dashboard implementation.
- [ ] Alert/privacy/retention validation evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Create actionable dashboards and alerts that distinguish load, capacity, dependency, security, and software failures

### Detailed technical checklist

- [ ] Build overview panels for request outcomes, pending/stalled backlog, convergence latency, capacity headroom, quota rejections, dependency health, and controller resources.
- [ ] Create separate alert conditions for capacity exhaustion, auth/policy outage, adapter failure, observation staleness, store/lease problems, retry storms, and security anomalies.
- [ ] Use multi-window/burn-rate or equivalent SLO-aware alerts where appropriate to reduce noise.
- [ ] Include release/config annotations so regressions correlate with changes.
- [ ] Link each alert to a specific runbook and owning escalation path.
- [ ] Inject synthetic failures and verify alert firing, routing, deduplication, recovery notification, and absence of cross-tenant data leakage.
- [ ] Adopt stable semantic names and identifiers for service, node, tenant, workload, VM, request, generation, adapter operation, release, and configuration.
- [ ] Distinguish accepted, pending, converged, rejected, degraded, retrying, quarantined, and terminal states in telemetry.
- [ ] Define metric type, unit, label set, cardinality budget, histogram buckets, and reset semantics for every exported metric.
- [ ] Use structured logs with stable event IDs, severity, causality/correlation fields, and mandatory secret/tenant-data redaction.
- [ ] Propagate trace context across transport, state, authorization, adapter, hypervisor/observation, and audit boundaries.
- [ ] Make health/readiness reflect real dependencies and convergence capability rather than process liveness alone.
- [ ] Define telemetry sampling, retention, privacy, export, and access-control policies with explicit high-cardinality safeguards.
- [ ] Test dashboards/alerts using synthetic failures and require runbook links, ownership, and actionable alert thresholds.

### Verification and negative-test checklist

- [ ] Use synthetic accepted, rejected, stalled, dependency-failed, security-denied, and recovery scenarios to verify emitted signals.
- [ ] Run cardinality and redaction tests at fleet scale; verify telemetry failure cannot cause control-path failure cascade.
- [ ] Verify every alert/detailed status can be traced to a runbook and accountable owner.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-059 — Benchmark/soak/fleet-scale certification environment and evidence.

**Current status:** Missing  
**Primary workstream:** Testing  
**Checklist coverage:** C088

### Objective

Create a benchmark/soak/fleet-scale certification environment with reproducible evidence.

### Referenced production requirements

- **INV-34-C088 — Testing & Certification:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Test plan and deterministic fixtures.
- [ ] Automated executable test suite.
- [ ] Machine-readable results and retained reproduction metadata.
- [ ] Component-specific design/implementation artifact demonstrating: Create a benchmark/soak/fleet-scale certification environment with reproducible evidence

### Detailed technical checklist

- [ ] Define a production-representative lab topology including real or representative hypervisor, guests, state store, authz, telemetry, and controller replicas.
- [ ] Automate environment provisioning and capture immutable environment/version fingerprints.
- [ ] Run long-duration soak with repeated expansions, observation delays, retries, controller rotations, and dependency maintenance.
- [ ] Run fleet-scale tests at expected and above-expected VM counts with realistic request/observation distributions.
- [ ] Collect performance, resource, leak, queue, error, and convergence data for the entire run.
- [ ] Archive raw data, logs/traces, test manifest, seed, config, artifact digests, and pass/fail summary.
- [ ] Define certification validity window and triggers that require recertification.
- [ ] Define a versioned test plan with explicit scope, prerequisites, topology, fixtures, deterministic seeds, and pass/fail criteria.
- [ ] Test both positive and negative behavior at the public boundary and assert durable state plus backend/guest truth, not only return codes.
- [ ] Cover boundary values, malformed inputs, stale generations, duplicate/replayed requests, partial progress, and dependency failures.
- [ ] Make tests isolated and reproducible; clean up VMs/state/leases/fixtures even after failure or interruption.
- [ ] Record environment, dependency, hypervisor/guest, schema, configuration, seed, and artifact versions with every test run.
- [ ] Persist failing seeds/corpora/traces and convert every discovered defect into a permanent regression case.
- [ ] Run required suites automatically in CI/certification and fail closed when a mandatory suite is skipped or unavailable.
- [ ] Publish machine-readable results and link them into the RTM and formal production exit gate.

### Verification and negative-test checklist

- [ ] Run the suite repeatedly with deterministic seeds plus randomized/stress variants and archive failing seeds/corpora.
- [ ] Validate assertions against durable state and real/emulated backend observations, not solely API return codes.
- [ ] Ensure every previously discovered defect receives a permanent regression test before closure.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-060 — Disaster/partition/reconnect/degraded-control-plane certification evidence.

**Current status:** Missing  
**Primary workstream:** Testing  
**Checklist coverage:** C089

### Objective

Certify disaster, partition, reconnect, and degraded-control-plane behavior end to end.

### Referenced production requirements

- **INV-34-C089 — Testing & Certification:** Create disaster, partition, reconnect, and degraded-control-plane tests.

### Required artifacts / deliverables

- [ ] Test plan and deterministic fixtures.
- [ ] Automated executable test suite.
- [ ] Machine-readable results and retained reproduction metadata.
- [ ] Component-specific design/implementation artifact demonstrating: Certify disaster, partition, reconnect, and degraded-control-plane behavior end to end

### Detailed technical checklist

- [ ] Test loss/recovery of controller node, multiple replicas, state-store leader/quorum, hypervisor management plane, observer, identity/authz, and telemetry sinks.
- [ ] Test partial and asymmetric network partitions plus extreme latency/packet loss.
- [ ] Test reconnect with stale controllers and large pending backlog, verifying fencing before replay.
- [ ] Test durable-state restore or reconstruction and reconcile against live VM CPU state.
- [ ] Test operation under explicitly allowed degraded modes and verify prohibited new expansions fail closed.
- [ ] Measure RTO/RPO/reconciliation time and compare to approved objectives.
- [ ] Retain incident-style timeline and machine-readable invariant checks for certification evidence.
- [ ] Define a versioned test plan with explicit scope, prerequisites, topology, fixtures, deterministic seeds, and pass/fail criteria.
- [ ] Test both positive and negative behavior at the public boundary and assert durable state plus backend/guest truth, not only return codes.
- [ ] Cover boundary values, malformed inputs, stale generations, duplicate/replayed requests, partial progress, and dependency failures.
- [ ] Make tests isolated and reproducible; clean up VMs/state/leases/fixtures even after failure or interruption.
- [ ] Record environment, dependency, hypervisor/guest, schema, configuration, seed, and artifact versions with every test run.
- [ ] Persist failing seeds/corpora/traces and convert every discovered defect into a permanent regression case.
- [ ] Run required suites automatically in CI/certification and fail closed when a mandatory suite is skipped or unavailable.
- [ ] Publish machine-readable results and link them into the RTM and formal production exit gate.

### Verification and negative-test checklist

- [ ] Run the suite repeatedly with deterministic seeds plus randomized/stress variants and archive failing seeds/corpora.
- [ ] Validate assertions against durable state and real/emulated backend observations, not solely API return codes.
- [ ] Ensure every previously discovered defect receives a permanent regression test before closure.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-061 — Machine-readable production acceptance evidence generated by the real `pk_core` gate. Framework tests cannot run in the supplied ZIP.

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C090, C100

### Objective

Generate the real machine-readable production acceptance evidence from `pk_core` and attach it to releases.

### Referenced production requirements

- **INV-34-C090 — Testing & Certification:** Require machine-readable acceptance evidence before certifying a Legacy CPU expansion path release for production.
- **INV-34-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Generate the real machine-readable production acceptance evidence from `pk_core` and attach it to releases

### Detailed technical checklist

- [ ] Run the production `pk_core` gate in an environment containing the pinned approved framework version.
- [ ] Ensure every C001..C100 control emits pass/fail/not-applicable/waived status with evidence references rather than a single aggregate boolean.
- [ ] Include source commit, artifact digest, dependency lock digest, environment fingerprint, test run IDs, timestamp, and signer/approver identity.
- [ ] Cryptographically sign or attest the evidence and store it immutably with the release.
- [ ] Fail certification when required evidence is missing, stale, produced against a different artifact, or generated with an unapproved framework version.
- [ ] Cross-check gate evidence against the RTM and formal exit-gate decision.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-062 — Support commitments/error-budget operations. Safety SLOs are declared, but paging policy, support hours and error-budget action rules are absent.

**Current status:** Partial  
**Primary workstream:** Operations  
**Checklist coverage:** C091, C097

### Objective

Operationalize SLOs, error budgets, support commitments, and response actions.

### Referenced production requirements

- **INV-34-C091 — Operations, Release & Governance:** Define production SLOs, error budgets, and support commitments for Legacy CPU expansion path.
- **INV-34-C097 — Operations, Release & Governance:** Define incident severity, paging, escalation, containment, and recovery procedures.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Operationalize SLOs, error budgets, support commitments, and response actions

### Detailed technical checklist

- [ ] Define service-level indicators for unsafe acceptance, false convergence, stale-write safety, availability, admission latency, convergence latency, and stalled backlog.
- [ ] Preserve zero-budget safety invariants separately from availability/performance error budgets.
- [ ] Define target windows and population (site/fleet/tenant tier) for each SLO.
- [ ] Define support hours and paging expectations by severity.
- [ ] Define error-budget burn actions: freeze rollout, disable new expansion, capacity increase, bug investigation, or release block.
- [ ] Publish monthly/quarterly SLO review evidence and link breaches to incidents/problem records.
- [ ] Prevent an availability objective from overriding a safety/security invariant.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-063 — Executable canary/staged rollout/rollback automation. The runbook describes the approach but no deployment system is bundled.

**Current status:** Partial  
**Primary workstream:** Operations  
**Checklist coverage:** C092

### Objective

Automate canary, staged rollout, rollback, and emergency disable.

### Referenced production requirements

- **INV-34-C092 — Operations, Release & Governance:** Define canary, staged rollout, rollback, and emergency-disable procedures for Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Automate canary, staged rollout, rollback, and emergency disable

### Detailed technical checklist

- [ ] Define rollout rings/scopes such as lab→canary site→small production cohort→progressive fleet.
- [ ] Automate preflight compatibility, config/provenance, state-store schema, authz, and dependency-health checks.
- [ ] Define promotion metrics and hard abort criteria for safety errors, convergence stalls, capacity anomalies, auth failures, or regression gates.
- [ ] Automate pause and emergency-disable propagation with confirmation that every controller has observed the new policy generation.
- [ ] Automate code/config rollback while preserving durable desired/observed truth and fencing pending operations.
- [ ] Record rollout actor, artifact/config digests, cohort, timestamps, observations, decision, and rollback evidence.
- [ ] Practice rollback from each rollout stage and verify no duplicate hot-plug actions.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-064 — Patch/vulnerability response and end-of-life SLA , including dependency update policy and emergency release process.

**Current status:** Missing  
**Primary workstream:** Operations  
**Checklist coverage:** C094

### Objective

Define patching, vulnerability response, dependency update, and end-of-life SLAs.

### Referenced production requirements

- **INV-34-C094 — Operations, Release & Governance:** Define patching, vulnerability response, and end-of-life SLAs for Legacy CPU expansion path.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Define patching, vulnerability response, dependency update, and end-of-life SLAs

### Detailed technical checklist

- [ ] Define severity taxonomy and remediation timelines for service code, Python/runtime, `pk_core`, hypervisor adapter, libraries, and base images.
- [ ] Continuously monitor SBOM components and vendor advisories for supported versions.
- [ ] Define emergency build/test/promotion path for critical vulnerabilities without bypassing safety invariants.
- [ ] Define supported release branches, patch cadence, deprecation notice, and end-of-support dates.
- [ ] Define how incompatible hypervisor/guest EOL drives compatibility-matrix changes and operator migration.
- [ ] Keep an exception process for missed SLA with owner, compensating control, and expiry.
- [ ] Exercise revocation of a compromised dependency/artifact and prove affected deployments can be identified from provenance.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-065 — Backup/restore/migration tooling for the durable state store once one is selected.

**Current status:** Missing  
**Primary workstream:** State Config  
**Checklist coverage:** C095

### Objective

Provide backup, restore, migration, and reconstruction tooling for durable state.

### Referenced production requirements

- **INV-34-C095 — Operations, Release & Governance:** Provide backup, restore, migration, or reconstruction procedures for Legacy CPU expansion path state where applicable.

### Required artifacts / deliverables

- [ ] Versioned schema/configuration or durable state definition.
- [ ] Transactional/recovery implementation.
- [ ] Migration/rollback/restore evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Provide backup, restore, migration, and reconstruction tooling for durable state

### Detailed technical checklist

- [ ] Define RPO/RTO and whether backup is required versus deterministic reconstruction from authoritative live systems.
- [ ] Back up durable desired/idempotency/config/lease metadata according to consistency guarantees; exclude ephemeral caches unless needed.
- [ ] Encrypt backups, restrict access, verify integrity, and record schema/application version compatibility.
- [ ] Provide restore tooling into isolated validation environment before production activation.
- [ ] After restore, reconcile every VM against live hypervisor/guest state before issuing side effects.
- [ ] Provide forward migration and rollback/abort semantics for state schema upgrades.
- [ ] Run recurring restore drills and retain measured RPO/RTO and reconciliation evidence.
- [ ] Define the authoritative schema, ownership, version, validation rules, and lifecycle for every configuration or mutable-state record introduced.
- [ ] Separate immutable code/artifacts from mutable configuration, durable state, secrets, and transient caches.
- [ ] Use atomic compare-and-swap or transactional semantics wherever partial updates could violate desired/observed/generation invariants.
- [ ] Define restart, replay, duplicate-delivery, stale-write, corruption, migration, and downgrade behavior before selecting a backend.
- [ ] Protect all records with tenant/VM scoping, least-privilege access, encryption where sensitive, and auditable administrative changes.
- [ ] Expose state/configuration version, activation generation, source/provenance, health, and replication/durability status to operators.
- [ ] Test crash points before/after durable writes and prove deterministic reconstruction from live hypervisor/guest observations.
- [ ] Provide backup/restore or reconstruction procedures and verify them against a clean environment before production certification.

### Verification and negative-test checklist

- [ ] Kill/restart processes at every write/commit/activation phase and verify state remains internally valid and reconstructable.
- [ ] Run concurrent writer, stale generation, duplicate request, schema upgrade/downgrade, and storage-unavailable cases.
- [ ] Restore or reconstruct into a clean environment and compare durable state against live hypervisor/guest truth before side effects.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-066 — Automated day-0/day-1/day-2 runbook actions. Human-readable steps exist; scripts/workflows and evidence capture do not.

**Current status:** Partial  
**Primary workstream:** Operations  
**Checklist coverage:** C096

### Objective

Automate day-0/day-1/day-2 runbook actions and evidence capture.

### Referenced production requirements

- **INV-34-C096 — Operations, Release & Governance:** Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Automate day-0/day-1/day-2 runbook actions and evidence capture

### Detailed technical checklist

- [ ] Create idempotent bootstrap checks for dependency versions, credentials, state store, schema, compatibility, config validation, and initial expansion-disabled posture.
- [ ] Automate deployment preflight, canary selection, rollout gates, health verification, and evidence capture.
- [ ] Automate steady-state checks for stalled backlog, dependency health, capacity freshness, lease health, SLO/error budget, and config drift.
- [ ] Automate emergency freeze/disable with scoped targeting and post-action verification.
- [ ] Automate routine reconciliation/reporting without ever invoking hot-unplug.
- [ ] Provide dry-run mode and explicit approval gates for destructive/production-affecting operator actions.
- [ ] Ensure scripts/workflows use service APIs rather than hidden direct database mutation where possible.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-067 — Incident severity, paging, escalation, containment and recovery procedure tied to a real owner/on-call system.

**Current status:** Missing  
**Primary workstream:** Operations  
**Checklist coverage:** C097

### Objective

Define incident severity, paging, escalation, containment, and recovery tied to real ownership.

### Referenced production requirements

- **INV-34-C097 — Operations, Release & Governance:** Define incident severity, paging, escalation, containment, and recovery procedures.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Define incident severity, paging, escalation, containment, and recovery tied to real ownership

### Detailed technical checklist

- [ ] Define severity examples: unauthorized expansion, duplicate hot-add, false convergence, cross-tenant impact, fleet stall, site dependency outage, and telemetry-only failure.
- [ ] Define paging targets and acknowledgement/escalation timers for each severity.
- [ ] Define immediate containment actions: disable new expansion, quarantine scope, revoke credentials, fence controller, or isolate adapter.
- [ ] Define evidence preservation requirements for state snapshots, audit events, logs/traces, release/config lineage, and hypervisor/guest facts.
- [ ] Define recovery sequencing and conditions for re-enabling expansion.
- [ ] Define post-incident review, corrective-action tracking, and regression-test requirements.
- [ ] Run tabletop/game-day exercises for at least unauthorized expansion, split-brain, and stalled fleet scenarios.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-068 — Recurring access/policy/dependency/configuration/architecture review process and evidence.

**Current status:** Missing  
**Primary workstream:** Operations  
**Checklist coverage:** C098

### Objective

Establish recurring reviews for access, policy, dependencies, configuration, and architecture.

### Referenced production requirements

- **INV-34-C098 — Operations, Release & Governance:** Perform recurring access, policy, dependency, configuration, and architecture reviews.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Establish recurring reviews for access, policy, dependencies, configuration, and architecture

### Detailed technical checklist

- [ ] Define review cadence and responsible reviewers for each review class.
- [ ] Review service identities/roles and remove unused or overbroad privileges.
- [ ] Review quota/precedence/freeze policy and confirm defaults remain fail closed.
- [ ] Review dependency/compatibility matrix, EOL dates, vulnerabilities, and pinned versions.
- [ ] Review production config drift, exceptions, stale feature flags, and emergency overrides.
- [ ] Review architecture/threat model after material hypervisor, state-store, transport, or trust-boundary changes.
- [ ] Capture findings, owner, due date, severity, and closure evidence in an auditable system.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-069 — Exception/waiver/technical-debt/deprecation registry with owner and expiry metadata.

**Current status:** Missing  
**Primary workstream:** Operations  
**Checklist coverage:** C099

### Objective

Maintain an exception, waiver, technical-debt, and deprecation registry.

### Referenced production requirements

- **INV-34-C099 — Operations, Release & Governance:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Maintain an exception, waiver, technical-debt, and deprecation registry

### Detailed technical checklist

- [ ] Define fields: unique ID, affected requirement/component, rationale, risk, compensating control, owner, approver, created/review/expiry dates, affected releases/environments.
- [ ] Prohibit permanent waivers for safety invariants such as no false convergence/no stale mutation unless the architecture itself changes and is reapproved.
- [ ] Automatically alert before expiry and block release when an expired waiver remains required.
- [ ] Link waivers to RTM and production exit-gate evidence.
- [ ] Track deprecated schemas/APIs/config flags with removal version and migration owner.
- [ ] Publish aggregate debt/waiver posture for recurring governance review without exposing secrets.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-070 — Formal production exit-gate workflow/sign-off requiring architecture, interface, security, resilience, performance, observability, rollback and ownership evidence before release.

**Current status:** Missing  
**Primary workstream:** Operations  
**Checklist coverage:** C100

### Objective

Implement a formal production exit gate that requires complete evidence before release.

### Referenced production requirements

- **INV-34-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Required artifacts / deliverables

- [ ] Runbook/governance workflow.
- [ ] Automation or service-catalog integration.
- [ ] Exercise/sign-off/audit evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Implement a formal production exit gate that requires complete evidence before release

### Detailed technical checklist

- [ ] Define mandatory gate domains: architecture/scope, requirements/RTM, interfaces, implementation/config, security, resilience, performance, observability, testing, rollout/rollback, ownership/support, supply chain, and licensing.
- [ ] For each domain, specify required machine-readable evidence artifact and freshness/version matching rules.
- [ ] Require zero open critical/high safety/security blockers and explicit disposition of lower-severity issues.
- [ ] Validate that evidence references the exact artifact digest/config/schema/compatibility matrix being promoted.
- [ ] Require named approvals from accountable engineering, security, operations/SRE, and release owner roles.
- [ ] Deny promotion automatically when a mandatory check is missing/failed/expired rather than allowing silent bypass.
- [ ] Archive the signed gate decision with the release and make it queryable during incidents/audits.
- [ ] Assign production owner, support hours, on-call/escalation path, and change approvers before enabling the component.
- [ ] Document day-0 bootstrap, day-1 deployment, day-2 operations, emergency disable, rollback, and recovery procedures.
- [ ] Automate production-affecting workflows where feasible and make every action idempotent, auditable, and safe to rerun.
- [ ] Use canary/staged rollout with explicit promotion/abort criteria derived from safety, convergence, error, and saturation signals.
- [ ] Maintain compatibility, lifecycle, patch/vulnerability, backup/recovery, and dependency support policies.
- [ ] Track operational exceptions and debt with owner, rationale, risk, mitigation, review date, and hard expiry.
- [ ] Exercise incident and recovery procedures periodically and retain evidence of the exercise and resulting corrective actions.
- [ ] Require formal release/production sign-off with machine-readable evidence rather than verbal or document-only claims.

### Verification and negative-test checklist

- [ ] Exercise the workflow in a staging/game-day environment using production-like identities, approvals, and evidence retention.
- [ ] Verify emergency actions work during partial dependency failure and are visible across all replicas/scopes.
- [ ] Audit a completed exercise/release and prove required decisions, actors, artifacts, and timestamps are reconstructable.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-071 — Repository packaging metadata and reproducible build definition (`pyproject.toml`/equivalent, dependency declaration, build backend, artifact metadata).

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C016, C031, C090

### Objective

Add standard packaging metadata and a reproducible build definition.

### Referenced production requirements

- **INV-34-C016 — Requirements & Semantics:** Define versioning and backward-compatibility requirements for Legacy CPU expansion path.
- **INV-34-C031 — Implementation & Configuration:** Select and pin approved implementations, versions, or specifications for Legacy CPU expansion path: ACPI hot-plug.
- **INV-34-C090 — Testing & Certification:** Require machine-readable acceptance evidence before certifying a Legacy CPU expansion path release for production.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Add standard packaging metadata and a reproducible build definition

### Detailed technical checklist

- [ ] Add `pyproject.toml` or equivalent with package name, semantic version source, Python requirement, build backend, package discovery, and optional/production dependencies.
- [ ] Generate version from a single authoritative source and validate package metadata matches `VERSION`/release tags.
- [ ] Declare `pk_core` strategy explicitly and separate test/dev dependencies from runtime dependencies.
- [ ] Build wheel/sdist or chosen deployable from a clean environment and verify contents contain schemas/docs/tests as intended.
- [ ] Add reproducible dependency lock and documented bootstrap command.
- [ ] Embed license/SPDX, project metadata, supported Python versions, and compatibility links.
- [ ] Add build verification that installs the produced artifact into a clean environment and runs standalone and framework gates.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-072 — CI pipeline running normal/optimized tests, static analysis, schema checks, security scans and release gates on every change.

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C070, C081-C090, C100

### Objective

Create CI that runs all quality, security, schema, test, and release gates on every change.

### Referenced production requirements

- **INV-34-C070 — Performance & Resource Efficiency:** Block releases that regress approved Legacy CPU expansion path startup, density, throughput, or tail-latency thresholds.
- **INV-34-C081 — Testing & Certification:** Create unit tests for deterministic Legacy CPU expansion path logic and state transitions.
- **INV-34-C082 — Testing & Certification:** Create contract tests for every public Legacy CPU expansion path interface.
- **INV-34-C083 — Testing & Certification:** Create integration tests with every supported adjacent layer and execution tier.
- **INV-34-C084 — Testing & Certification:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Legacy CPU expansion path.
- **INV-34-C085 — Testing & Certification:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Legacy CPU expansion path.
- **INV-34-C086 — Testing & Certification:** Create concurrency and race-condition tests for shared/distributed Legacy CPU expansion path state.
- **INV-34-C087 — Testing & Certification:** Create security tests derived directly from the Legacy CPU expansion path threat model.
- **INV-34-C088 — Testing & Certification:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Legacy CPU expansion path.
- **INV-34-C089 — Testing & Certification:** Create disaster, partition, reconnect, and degraded-control-plane tests.
- **INV-34-C090 — Testing & Certification:** Require machine-readable acceptance evidence before certifying a Legacy CPU expansion path release for production.
- **INV-34-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Create CI that runs all quality, security, schema, test, and release gates on every change

### Detailed technical checklist

- [ ] Run clean install/build on supported Python versions and at least normal plus optimized (`-O`) test modes where behavior could differ.
- [ ] Run unit, contract, integration-emulator, schema validation, concurrency, fuzz smoke, and static import/compile checks.
- [ ] Run lint/type/static security/secret/dependency vulnerability/license checks.
- [ ] Validate RTM completeness, compatibility data, configuration schemas, generated artifacts, and version consistency.
- [ ] Run supply-chain/SBOM/provenance generation and verify artifact digests.
- [ ] Use protected branches and required checks; production release jobs must consume artifacts built by CI, not rebuild ad hoc.
- [ ] Publish machine-readable test/gate results and retain logs/artifacts long enough for release audit.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-073 — Static type-check/lint policy and automated enforcement (tool configuration and CI execution).

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** C081, C090, C100

### Objective

Define and enforce static type checking and lint policy.

### Referenced production requirements

- **INV-34-C081 — Testing & Certification:** Create unit tests for deterministic Legacy CPU expansion path logic and state transitions.
- **INV-34-C090 — Testing & Certification:** Require machine-readable acceptance evidence before certifying a Legacy CPU expansion path release for production.
- **INV-34-C100 — Operations, Release & Governance:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Define and enforce static type checking and lint policy

### Detailed technical checklist

- [ ] Select pinned tools and versions appropriate to the Python codebase and record configuration in repository.
- [ ] Enable strict-enough type checks for public contracts, state records, adapter interfaces, error objects, and configuration models.
- [ ] Enforce import hygiene, unreachable/dead code, complexity or bug-prone patterns, unsafe exception handling, and formatting consistently.
- [ ] Ban production `assert` for runtime validation and flag dangerous dynamic execution/shell patterns.
- [ ] Define suppression policy requiring inline rationale, issue/owner, and preferably expiry for security-relevant ignores.
- [ ] Run tools on source and tests in CI; fail on new violations rather than only reporting them.
- [ ] Periodically ratchet baseline debt down until no grandfathered violations remain.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

## MC-074 — Repository license/SPDX declaration. No license was supplied, so the audit did not invent one.

**Current status:** Missing  
**Primary workstream:** Build Supply  
**Checklist coverage:** Governance/release completeness

### Objective

Add an explicit repository license and SPDX declarations without inventing ownership terms.

### Required artifacts / deliverables

- [ ] Build/package/policy configuration.
- [ ] Signed/SBOM/provenance/compliance artifacts as applicable.
- [ ] CI/release-gate evidence.
- [ ] Component-specific design/implementation artifact demonstrating: Add an explicit repository license and SPDX declarations without inventing ownership terms

### Detailed technical checklist

- [ ] Have the authorized rights holder choose and approve the project license.
- [ ] Add the canonical license text in a top-level `LICENSE`/`COPYING` file and record copyright notices as appropriate.
- [ ] Add SPDX license identifier headers or metadata to source/artifact files according to project policy.
- [ ] Ensure package metadata, SBOM, README, distribution artifacts, and documentation report the same license identifier.
- [ ] Run license-compliance scanning for transitive dependencies and define policy for incompatible/unknown licenses.
- [ ] Document third-party notices/attribution obligations and include them in distributed artifacts where required.
- [ ] Add CI checks preventing missing/unknown SPDX metadata and unauthorized license changes.
- [ ] Define a reproducible source-to-artifact build using pinned toolchain/dependencies and a machine-readable package manifest.
- [ ] Verify dependency/artifact digests and provenance; prohibit unreviewed floating versions in production builds.
- [ ] Generate an SBOM and license inventory for every release artifact and its transitive dependencies.
- [ ] Run static analysis, type/lint checks, dependency vulnerability checks, secret scanning, and policy gates in CI.
- [ ] Sign release artifacts/attestations and verify them again at promotion or deployment boundaries.
- [ ] Support deterministic clean-room rebuild or document the exact unavoidable sources of non-determinism.
- [ ] Publish version, build metadata, compatibility constraints, provenance, and checksums alongside the release.
- [ ] Define emergency dependency update and revocation procedures for compromised packages/toolchains.

### Verification and negative-test checklist

- [ ] Rebuild/install/verify from a clean environment using only declared inputs and compare produced artifact metadata/digests where reproducibility is required.
- [ ] Test tampered, unsigned, vulnerable, unlicensed/unknown, wrong-version, and revoked dependency/artifact paths and verify promotion is blocked.
- [ ] Verify CI/release evidence is bound to the exact promoted artifact digest and cannot be substituted from another run.

### Definition of Done / closure evidence

- [ ] Implementation is merged/released with an identified owner and no unresolved critical/high defects for this component.
- [ ] The RTM links this component to its exact requirement IDs, implementation locations, automated test IDs, and operational evidence.
- [ ] Machine-readable test/gate results identify source revision, build/release artifact digest, dependency/config versions, environment, and timestamp.
- [ ] Security, resilience, observability, and rollback/recovery impacts are reviewed and any exception is registered with owner and expiry.
- [ ] Documentation/runbooks/compatibility data are updated and a clean reviewer can reproduce the acceptance evidence.
- [ ] The formal production exit gate records this component as accepted for the exact release/configuration scope being promoted.

---

# Final integrated closure gate

After MC-001 through MC-074 are individually satisfied, run an integrated certification pass rather than treating component closure as sufficient in isolation.

- [ ] Build the production artifact from a clean, declared, reproducible environment and verify package metadata, license, SBOM, signatures/provenance, dependency lock, and checksums.
- [ ] Deploy the exact artifact/configuration to the certification environment using the automated day-0/day-1 workflow.
- [ ] Run authenticated/authorized request paths through durable state, quota/precedence, ownership/lease, real hypervisor adapter, and independent guest observation.
- [ ] Prove accepted requests never exceed configured/host/quota constraints and never report convergence until independent observation reaches desired state.
- [ ] Prove retries, failover, process crash, state-store failover, network partition, stale controller, and reconnect cannot cause duplicate or regressive CPU actions.
- [ ] Run adversarial security, fuzz/property, concurrency/race, fault injection, compatibility, contract, integration, disaster, benchmark, soak, and fleet-scale certification suites.
- [ ] Verify health/readiness, metrics, structured logs, traces, audit records, explain view, dashboards, and alerts across success/failure/recovery cases.
- [ ] Validate canary/staged rollout, emergency disable, rollback, backup/restore/reconstruction, incident response, and support escalation in a game day.
- [ ] Generate the real `pk_core` machine-readable production evidence for INV-34-C001..C100 and cross-check it against the RTM.
- [ ] Require formal architecture, security, test/certification, SRE/operations, release, and accountable-owner sign-off against the exact artifact/configuration digests.

**Production-ready means the evidence above is complete and reproducible. It does not mean that every checklist box merely has a document associated with it.**
