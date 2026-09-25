# PLN-05 Elasticity Plane v4.1.1
## Comprehensive Missing-Component Remediation Checklists

**Source audit:** `PLN05_AUDIT_REPORT_4.1.1.md`  
**Audited repository:** PLN-05 Elasticity Plane v4.1.1  
**Residual inventory:** 34 missing/partial production components  
**Purpose:** Convert every residual audit gap into an implementation-grade engineering checklist with explicit artifacts, verification, evidence, and definition-of-done criteria.

> **Use of this document**
>
> - Check boxes are intended to be completed against code/evidence, not by documentation assertion alone.
> - “Implemented” is not equivalent to “verified.” A component closes only when its acceptance criteria and evidence gates are satisfied.
> - Proposed paths are recommendations; they may be adapted, but a single authoritative source should exist for each artifact.
> - Any requirement intentionally deferred should use a formal waiver with owner, risk, compensating controls, and expiry.
> - Priorities below are recommended remediation priorities derived from dependency/risk ordering, not changes to the original checklist.

---

## Global completion gates

Before **any** MC item is closed, verify all of the following:

- [ ] The component has a normative specification using explicit SHALL/SHALL NOT language where behavior is externally significant.
- [ ] The implementation is present in the shipped repository/package and not only described in README text.
- [ ] Input validation is fail-closed and boundary validation occurs before unsafe state mutation.
- [ ] Error handling is deterministic, typed/machine-readable where appropriate, and does not leak secrets.
- [ ] Resource use is bounded for queues, retries, concurrency, payload size, and retained state where relevant.
- [ ] Security/tenant boundaries are preserved under normal, error, restart, overload, and partition conditions.
- [ ] Unit tests cover happy path, boundary conditions, invalid input, and failure paths.
- [ ] Integration/contract tests exercise actual external boundaries rather than bypassing parsers or adapters.
- [ ] Any state/config/schema format is versioned and has compatibility/migration behavior.
- [ ] Observability is sufficient to diagnose success/failure without unsafe high-cardinality or secret leakage.
- [ ] Requirement → implementation → verification → evidence mappings are recorded.
- [ ] CI executes all mandatory verification with **no unexpected skips**.
- [ ] Release evidence includes machine-readable pass/fail results.
- [ ] Operator/developer documentation is updated.
- [ ] An accountable owner/reviewer approves closure.

---

## Recommended dependency order

1. **Architecture and requirements:** MC-01 → MC-02 → MC-03 → MC-04  
2. **Interfaces and reproducibility:** MC-05 → MC-06 → MC-07 → MC-08 → MC-09 → MC-10  
3. **Security:** MC-11 → MC-12 → MC-13 → MC-14  
4. **Resilience and state:** MC-15 → MC-16 → MC-17 → MC-18 → MC-19 → MC-20  
5. **Performance:** MC-21 → MC-22 → MC-23  
6. **Operations/observability:** MC-24 → MC-25 → MC-26 → MC-27  
7. **Robustness/release:** MC-28 → MC-29 → MC-30 → MC-31  
8. **Repository completeness/automation/governance:** MC-32 → MC-33 → MC-34

---

# MC-01 — Authoritative scope / ADR resolution
**Recommended priority:** P0 — architecture blocker  
**Objective:** Establish one authoritative definition of PLN-05 so the implementation, contract, tests, checklist, and release evidence cannot disagree about whether PLN-05 is a hysteretic capacity-target controller or also owns snapshot/restore, Dandelion-style microfunctions, and HyperFlux-style resource reassignment.  
**Dependencies:** None. This should precede requirements, schema, interface, and acceptance work.

## Required deliverables
- [ ] `docs/adr/ADR-0001-pln05-authoritative-scope.md`
- [ ] Updated `CHECKLIST.json`, `contract.py`, `README.md`, and acceptance evidence
- [ ] Machine-readable scope declaration, e.g. `spec/pln05_scope.yaml`
- [ ] Migration/deprecation note for whichever interpretation is retired

## Component-specific implementation checklist
- [ ] Identify every source that currently asserts PLN-05 responsibilities: `CHECKLIST.json`, `contract.py`, `README.md`, implementation modules, tests, generated evidence, and sibling-interface documentation.
- [ ] Create a side-by-side responsibility matrix for: demand observation, hysteresis, capacity target calculation, placement, provisioning, resource reassignment, snapshot, restore, microfunction lifecycle, failover, and execution ownership.
- [ ] Classify each responsibility as **OWN**, **ORCHESTRATE**, **CALL**, **OBSERVE**, or **OUT OF SCOPE**.
- [ ] Select a single authoritative architecture interpretation and record the decision in an ADR with status, date, approvers, context, alternatives, consequences, and superseded material.
- [ ] State the exact production responsibility in SHALL/SHALL NOT language.
- [ ] Define the source-of-truth precedence order when README, checklist, contract, and code disagree.
- [ ] If snapshot/restore remains in scope, identify the owning API, durability model, restore consistency point, timeout semantics, and interaction with elasticity decisions.
- [ ] If Dandelion-style microfunctions remain in scope, define lifecycle, scheduling authority, isolation boundary, artifact model, invocation protocol, and failure ownership.
- [ ] If HyperFlux-style resource reassignment remains in scope, define provider authority, placement constraints, resource accounting, fencing, and rollback.
- [ ] If the implemented capacity-target-only design is authoritative, explicitly deprecate C010/C011 language that implies execution/resource ownership and replace it with capacity-control semantics.
- [ ] Document backward-compatibility impact on sibling components and any contract versions that must change.
- [ ] Define architecture invariants that future changes may not violate, including ownership boundaries and forbidden ambient authority.
- [ ] Update tests so they fail if documentation/specification drifts from the selected scope.
- [ ] Add a repository check that verifies all declared scope/version identifiers agree.
- [ ] Record unresolved questions and explicit non-goals rather than leaving ambiguous behavior implicit.
- [ ] Obtain explicit approval from the accountable architecture owner before closing this component.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Exactly one production scope is normative and all repository artifacts agree with it.
- [ ] No checklist requirement demands behavior that the accepted contract forbids.
- [ ] Scope drift is detectable by automated validation in CI.
- [ ] Every sibling dependency can determine whether PLN-05 owns, calls, or excludes each major responsibility.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-02 — Ownership and escalation record
**Recommended priority:** P0 — operational accountability  
**Objective:** Create durable ownership metadata and operational escalation paths for production, security, release, and incident decisions.  
**Dependencies:** MC-01 should identify the final production boundary.

## Required deliverables
- [ ] `CODEOWNERS` or equivalent ownership metadata
- [ ] `docs/operations/ownership-and-escalation.md`
- [ ] `ops/oncall.yaml` or equivalent machine-readable owner/escalation manifest
- [ ] Approval and review cadence recorded in release evidence

## Component-specific implementation checklist
- [ ] Name the accountable service owner, technical owner, release approver, security contact, and operational on-call role.
- [ ] Separate **role identifiers** from personal contact data so the repository remains maintainable and privacy-safe.
- [ ] Define primary and secondary escalation paths for availability, security, data-integrity, and dependency incidents.
- [ ] Define business-hours and after-hours paging expectations.
- [ ] Declare the support boundary between PLN-05 and upstream/downstream sibling components.
- [ ] Define which team owns externally supplied demand authenticity, capacity-limit correctness, provider outages, and controller correctness.
- [ ] Specify who may approve emergency disable, freeze, rollback, configuration override, or authority-ceiling changes.
- [ ] Define ownership handoff requirements and minimum notice when maintainers change.
- [ ] Establish review cadence for owner metadata and escalation routes.
- [ ] Add stale-owner detection to CI or release review, e.g. required non-empty ownership fields and last-reviewed date.
- [ ] Map incident severity levels to escalation roles.
- [ ] Define response expectations for critical vulnerabilities and production regressions.
- [ ] Identify the owner for checklist waivers and technical-debt expirations.
- [ ] Document how operators locate current escalation information during a control-plane outage.
- [ ] Ensure ownership metadata is referenced from README/runbooks rather than duplicated inconsistently.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] A responder can identify the correct owner and escalation role without tribal knowledge.
- [ ] Every privileged operational action has an accountable approving role.
- [ ] Ownership metadata has a documented review date and does not rely on an individual-only contact.
- [ ] Release evidence records the accountable approver.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-03 — Context / NFR / semantics specification
**Recommended priority:** P0 — requirements foundation  
**Objective:** Define the environment, semantics, lifecycle, non-functional requirements, partition behavior, and policy precedence required for predictable operation across cloud, datacenter, near-edge, and far-edge deployments.  
**Dependencies:** MC-01; informs MC-05 through MC-31.

## Required deliverables
- [ ] `spec/pln05_semantics.md`
- [ ] `spec/pln05_nfr.yaml`
- [ ] `spec/pln05_state_machine.mmd` or equivalent state diagram
- [ ] Environment profile matrix for cloud/DC/near-edge/far-edge

## Component-specific implementation checklist
- [ ] Define supported deployment contexts: public cloud, private cloud, datacenter, near-edge, far-edge, disconnected/occasionally connected edge.
- [ ] Define assumptions for clock quality, network latency, packet loss, bandwidth, power stability, storage durability, and control-plane reachability per context.
- [ ] Specify outcome classes for every observation cycle: scale-up, scale-down, hold, constrained-hold, stale-input-hold, frozen, degraded, error, and recovery.
- [ ] Define the controller lifecycle state machine including initialization, ready, active, degraded, frozen, quarantined, draining, stopped, and recovery transitions.
- [ ] Define authoritative time semantics: monotonic vs wall clock, grace-window timing, stale-demand age, and behavior during clock discontinuity.
- [ ] Set explicit NFRs for reaction latency p50/p95/p99, availability, recovery time, recovery point, throughput, memory, CPU, and acceptable decision error rate.
- [ ] Define demand freshness thresholds and the exact action when demand becomes stale or unavailable.
- [ ] Define behavior under network partition between PLN-05 and demand source, provider/control plane, policy service, and observability backend.
- [ ] Specify precedence among hard safety ceiling, hard floor, policy constraints, site limits, tenancy limits, provider limits, operator override, and demand signal.
- [ ] Define conflict resolution for contradictory or rapidly changing policies.
- [ ] Define consistency expectations for floor/ceiling changes while a grace window is in progress.
- [ ] Define idempotency and monotonicity expectations for repeated observations.
- [ ] Specify numerical domains, units, rounding rules, saturation behavior, and overflow/underflow handling.
- [ ] Define supported scale magnitudes and rate-of-change limits.
- [ ] Document tenant and workload semantics: whether state is per workload, per tenant, per site, or global.
- [ ] State privacy/data-classification expectations for demand and telemetry fields.
- [ ] Map every NFR to a measurable verification method and acceptance threshold.
- [ ] Version the semantics specification and define compatibility rules for semantic changes.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every externally visible state and outcome has a normative definition.
- [ ] Partition, stale-input, and clock-failure behavior is deterministic and testable.
- [ ] All NFRs are measurable and linked to tests/benchmarks.
- [ ] Policy precedence is unambiguous and encoded consistently in implementation/tests.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-04 — Requirements traceability matrix
**Recommended priority:** P0 — governance / evidence  
**Objective:** Create a machine-readable bidirectional mapping between every requirement, implementation element, test, evidence artifact, owner, status, and release gate.  
**Dependencies:** MC-01 and MC-03.

## Required deliverables
- [ ] `traceability/requirements.yaml`
- [ ] Generated `traceability/REQUIREMENTS_MATRIX.md`
- [ ] CI validator for orphaned/stale mappings
- [ ] Release snapshot of the matrix

## Component-specific implementation checklist
- [ ] Assign a stable immutable identifier to every requirement, including C001-C100 and any new SHALL-level requirements.
- [ ] Record requirement source, version, rationale, criticality, and acceptance criterion.
- [ ] Map each requirement to one or more implementation files/symbols when applicable.
- [ ] Map each requirement to one or more verification tests, benchmarks, analyses, reviews, or operational exercises.
- [ ] Map each requirement to evidence output paths and evidence format.
- [ ] Record requirement owner and reviewer role.
- [ ] Track status using controlled values such as planned, implemented, verified, waived, deprecated, superseded.
- [ ] Record dependency relationships among requirements.
- [ ] Represent partial coverage explicitly; do not treat a file citation as proof of behavioral compliance.
- [ ] Record waiver ID and expiry date for any intentionally unmet requirement.
- [ ] Add reverse mappings from code/test/evidence back to requirements to detect unclaimed implementation.
- [ ] Validate that deleted or renamed files do not leave stale evidence links.
- [ ] Generate human-readable reports from the machine-readable source; do not maintain two independent matrices.
- [ ] Fail CI when a mandatory production requirement has no verification path.
- [ ] Fail release gating when mandatory requirements remain unverified unless an approved non-expired waiver exists.
- [ ] Preserve matrix snapshots per released version for auditability.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every mandatory requirement has an owner, implementation mapping, verification mapping, and evidence mapping or approved waiver.
- [ ] The matrix is generated reproducibly and validated in CI.
- [ ] Traceability is bidirectional and stale references fail automated checks.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-05 — Typed external schemas
**Recommended priority:** P0 — interface correctness  
**Objective:** Define concrete, versioned, machine-validatable schemas for `PK_DEMAND/1`, `PK_CAPACITY_LIMITS/1`, and `PK_CAPACITY_TARGET/1`, including evolution and compatibility rules.  
**Dependencies:** MC-01 and MC-03.

## Required deliverables
- [ ] `schemas/pk_demand_v1.json` or equivalent IDL
- [ ] `schemas/pk_capacity_limits_v1.json`
- [ ] `schemas/pk_capacity_target_v1.json`
- [ ] Generated language bindings/validators and golden examples

## Component-specific implementation checklist
- [ ] Choose and document the canonical schema technology: JSON Schema, Protobuf, Avro, WIT, OpenAPI schema, or another versioned IDL.
- [ ] Assign stable schema IDs and semantic versions.
- [ ] Define every field with type, required/optional status, units, allowed range, default semantics, and nullability.
- [ ] Use explicit numeric constraints to reject NaN, Infinity, negative capacity, inverted floor/ceiling, and impossible utilization.
- [ ] Define identifiers for tenant, workload, site, source, request, correlation, and schema version where required.
- [ ] Define event/observation timestamps and freshness semantics.
- [ ] Define demand confidence/quality metadata if multiple demand sources or inferred signals are possible.
- [ ] Define capacity-limit provenance and authority source.
- [ ] Define capacity-target reason/outcome fields and whether the target is absolute, delta, or normalized.
- [ ] Define extensibility rules for unknown fields and forward compatibility.
- [ ] Define breaking vs non-breaking schema changes.
- [ ] Define schema negotiation or supported-version behavior when peers differ.
- [ ] Generate runtime validators and ensure boundary validation occurs before business logic.
- [ ] Create canonical valid examples for minimum, nominal, floor, ceiling, and boundary values.
- [ ] Create invalid examples for malformed type, missing required field, unknown critical version, NaN/Infinity, stale timestamps, negative values, and authority violations.
- [ ] Add schema linting and compatibility checks to CI.
- [ ] Publish checksum/version metadata for released schemas.
- [ ] Ensure error responses identify schema/version failure without echoing sensitive payloads.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] All external inputs/outputs are validated against a released schema before use.
- [ ] Boundary-value and invalid-payload tests cover every field constraint.
- [ ] Backward/forward compatibility rules are automated in CI.
- [ ] Schema versions are carried in protocol exchanges or otherwise unambiguously negotiated.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-06 — Boundary IAM / capability specification
**Recommended priority:** P0 — security boundary  
**Objective:** Specify and enforce authentication, authorization, trust establishment, and least-privilege capabilities for every external actor and interface.  
**Dependencies:** MC-01, MC-05, MC-11.

## Required deliverables
- [ ] `security/iam-model.md`
- [ ] `security/capabilities.yaml`
- [ ] Policy definitions and enforcement hooks
- [ ] IAM conformance tests

## Component-specific implementation checklist
- [ ] Enumerate actor classes: demand reporter, operator, policy service, provider adapter, sibling plane, telemetry collector, release agent, and emergency administrator.
- [ ] Define trust bootstrap for each actor class.
- [ ] Define accepted workload identity mechanisms such as mTLS SPIFFE/SPIRE identity, signed tokens, cloud workload identity, or equivalent.
- [ ] Define authentication failure behavior and audit requirements.
- [ ] Define authorization actions granularly: submit demand, update limits, read status, freeze, unfreeze, quarantine, change config, publish target, retrieve evidence.
- [ ] Apply default-deny authorization.
- [ ] Separate read, control, and administrative capabilities.
- [ ] Prevent demand submitters from modifying authority ceilings unless explicitly authorized by a distinct capability.
- [ ] Define tenant scoping and prevent cross-tenant identity reuse.
- [ ] Define site/environment scoping where edge or multi-site operation is supported.
- [ ] Define credential/session lifetime and rotation requirements.
- [ ] Define replay-resistant proof requirements for control operations.
- [ ] Specify how peer identity is bound to schema/source metadata to prevent source spoofing.
- [ ] Define break-glass access, approval, expiry, and mandatory audit behavior.
- [ ] Enforce least privilege in process/container/VM runtime permissions as well as API policy.
- [ ] Add negative tests for unauthorized, expired, wrong-tenant, wrong-site, and privilege-escalation attempts.
- [ ] Version capability policy and include policy version in explain/audit evidence.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every externally callable operation has an explicit authenticated actor and authorization rule.
- [ ] Default-deny behavior is verified by negative tests.
- [ ] No untrusted actor can raise PLN-05 authority or cross tenant/site boundaries.
- [ ] Privileged emergency access is time-bounded and auditable.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-07 — Interface reliability and error contract
**Recommended priority:** P0 — protocol resilience  
**Objective:** Define consistent timeout, cancellation, retry, idempotency, backpressure, limits, and structured error semantics across every public interface.  
**Dependencies:** MC-03, MC-05, MC-06.

## Required deliverables
- [ ] `spec/interface_reliability.md`
- [ ] `schemas/error_v1.*`
- [ ] Client/server timeout and retry defaults
- [ ] Interface reliability contract tests

## Component-specific implementation checklist
- [ ] Enumerate every synchronous and asynchronous interface.
- [ ] Define connect, handshake, request, response, idle, and end-to-end deadlines.
- [ ] Define cancellation propagation semantics and cleanup obligations.
- [ ] Classify operations as idempotent, conditionally idempotent, or non-idempotent.
- [ ] Define idempotency-key format, scope, retention, and duplicate-response behavior where needed.
- [ ] Define retryable vs non-retryable error classes.
- [ ] Specify maximum attempts, exponential backoff parameters, jitter strategy, and retry budget.
- [ ] Ensure retries cannot amplify stale demand or duplicate target application.
- [ ] Define queue bounds and backpressure signals.
- [ ] Define overload behavior: reject, shed, coalesce, sample, or defer.
- [ ] Create stable machine-readable error codes with category, retryability, severity, and correlation ID.
- [ ] Prevent internal stack traces, secrets, or raw untrusted payloads from leaking in errors.
- [ ] Define maximum request size, nesting depth, field counts, and rate limits.
- [ ] Define behavior for unknown schema versions and partially supported capabilities.
- [ ] Define ordering guarantees if events are streamed.
- [ ] Define duplicate/out-of-order event handling.
- [ ] Add protocol tests for timeout, cancel, retry, duplicate, overload, malformed error, and recovery.
- [ ] Document client guidance so sibling components do not implement incompatible retry logic.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every interface has deterministic deadline, retry, and failure behavior.
- [ ] Duplicate/replayed requests cannot cause duplicated authority changes.
- [ ] Backpressure and overload behavior is bounded and test-covered.
- [ ] Error codes are stable, machine-readable, and correlation-friendly.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-08 — Protocol examples and conformance fixtures
**Recommended priority:** P1 — interoperability  
**Objective:** Provide golden valid/invalid payloads and automated contract tests that make interface compliance independently verifiable by sibling implementations.  
**Dependencies:** MC-05 and MC-07.

## Required deliverables
- [ ] `fixtures/protocol/valid/`
- [ ] `fixtures/protocol/invalid/`
- [ ] `tests/contract/`
- [ ] Fixture manifest with expected result/error

## Component-specific implementation checklist
- [ ] Create at least one golden fixture for every public message type and schema version.
- [ ] Cover minimum, nominal, maximum, floor, ceiling, zero-load, and boundary-value cases.
- [ ] Create invalid fixtures for each required-field omission.
- [ ] Create wrong-type and out-of-range fixtures for every constrained field.
- [ ] Create stale timestamp and future-skew fixtures.
- [ ] Create wrong-tenant, wrong-site, and unauthorized-source fixtures where identity metadata applies.
- [ ] Create unknown-version and forward-compatible-extension fixtures.
- [ ] Create duplicate, reordered, and replayed message sequences.
- [ ] Create invalid limit combinations such as floor > ceiling.
- [ ] Create non-finite numeric cases where the serialization format permits them.
- [ ] Record expected status, error code, and side-effect expectation for every invalid fixture.
- [ ] Make fixture files immutable test assets with stable names.
- [ ] Provide a fixture manifest containing schema version and checksum.
- [ ] Build contract tests that load fixtures through the real boundary validator, not internal constructors that bypass parsing.
- [ ] Expose fixtures for sibling repositories to consume.
- [ ] Test round-trip serialization/deserialization without semantic drift.
- [ ] Add mutation testing or generated negative variants to avoid hand-picked blind spots.
- [ ] Run conformance fixtures in CI and include results in release evidence.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] A third-party sibling implementation can validate interoperability using repository-contained fixtures.
- [ ] Every schema validation rule has at least one positive or negative fixture.
- [ ] Fixture tests exercise real protocol boundaries and produce machine-readable results.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-09 — Build / package / dependency manifest
**Recommended priority:** P0 — reproducibility  
**Objective:** Make installation, dependency resolution, packaging, and compatibility reproducible from the repository without hidden environment assumptions.  
**Dependencies:** MC-01; supports almost every later component.

## Required deliverables
- [ ] `pyproject.toml`
- [ ] Lock/constraints file
- [ ] Build metadata and reproducible package artifact
- [ ] Dependency compatibility manifest

## Component-specific implementation checklist
- [ ] Define the canonical Python/runtime version range.
- [ ] Create `pyproject.toml` with package name, version, dependencies, optional groups, entry points, license metadata, and build backend.
- [ ] Declare `pk_core` explicitly with compatible version bounds or provide a repository-contained substitute if that is the architecture decision.
- [ ] Declare sibling contract/runtime package versions required for supported integration tiers.
- [ ] Pin build-tool versions used for release packaging.
- [ ] Add a lock or constraints mechanism appropriate to the deployment model.
- [ ] Separate runtime, test, benchmark, docs, and development dependencies.
- [ ] Eliminate undeclared imports and environment-only dependencies.
- [ ] Document offline installation behavior and package mirror requirements if edge deployment requires it.
- [ ] Create deterministic bootstrap commands for clean Windows/Linux CI images as applicable.
- [ ] Build both source distribution and wheel/package artifact where appropriate.
- [ ] Verify installation into a clean isolated environment.
- [ ] Verify uninstall/reinstall and upgrade from the previous supported release.
- [ ] Generate package checksums and provenance metadata.
- [ ] Define dependency update cadence and compatibility testing process.
- [ ] Add dependency vulnerability scanning and license-policy checks.
- [ ] Ensure the version is sourced from one canonical location and checked against package metadata/README/evidence.
- [ ] Fail CI when the dependency graph is unresolved or lock data is stale.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] A clean environment can install and test PLN-05 using repository-declared commands only.
- [ ] `pk_core` and sibling compatibility are explicit rather than assumed.
- [ ] Released artifacts are reproducible, versioned, checksummed, and provenance-linked.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-10 — Declarative configuration subsystem
**Recommended priority:** P0 — safe operations  
**Objective:** Replace ad-hoc/in-memory configuration with validated, versioned, provenance-aware, atomically activated configuration supporting overlays, rollback, and secret-safe handling.  
**Dependencies:** MC-03, MC-05, MC-06, MC-09.

## Required deliverables
- [ ] `config/schema.*`
- [ ] `config/defaults.*`
- [ ] Configuration loader/validator module
- [ ] Activation/rollback journal and tests

## Component-specific implementation checklist
- [ ] Define a versioned configuration schema for thresholds, grace periods, floors, ceilings, stale-input policy, telemetry, and safety controls.
- [ ] Declare units and valid ranges for every field.
- [ ] Reject unknown critical fields and malformed versions fail-closed.
- [ ] Separate immutable package defaults from mutable site/environment configuration.
- [ ] Define overlay precedence: package default → environment/site → tenant/workload → operator emergency override, or the accepted model.
- [ ] Implement deep merge semantics explicitly; avoid ambiguous merge behavior for lists/maps.
- [ ] Record configuration source, revision, author/issuer, checksum, activation timestamp, and schema version.
- [ ] Validate the entire candidate configuration before activation.
- [ ] Activate multi-field changes atomically so readers never observe half-applied state.
- [ ] Preserve the last-known-good configuration.
- [ ] Implement explicit rollback with audit record and reason.
- [ ] Define behavior when a new config is invalid, partially unreadable, or references unsupported capabilities.
- [ ] Support dry-run validation and diff generation before activation.
- [ ] Define whether config updates reset hysteresis/grace state and test the decision.
- [ ] Prevent secrets from entering ordinary config where possible; where unavoidable, reference secret stores rather than embedding plaintext.
- [ ] Redact secret-bearing values from logs, errors, status, and evidence.
- [ ] Protect configuration files/objects with integrity checks and appropriate permissions.
- [ ] Add property tests for overlay precedence and atomicity.
- [ ] Add crash/restart tests around activation to ensure no torn configuration state.
- [ ] Expose active configuration version/checksum in the status surface.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Invalid configuration cannot become active.
- [ ] Configuration transitions are atomic, provenance-recorded, reversible, and restart-safe.
- [ ] Operators can prove exactly which configuration produced a given decision.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-11 — Complete threat model and artifact trust chain
**Recommended priority:** P0 — security architecture  
**Objective:** Establish a formal threat model covering tenants, supply chain, control plane, identity, providers, operators, telemetry, and artifacts, then enforce artifact provenance and approved-version policy.  
**Dependencies:** MC-01, MC-06, MC-09.

## Required deliverables
- [ ] `security/threat-model.md`
- [ ] Data-flow/trust-boundary diagrams
- [ ] SBOM generation configuration
- [ ] Artifact signature/provenance verification policy

## Component-specific implementation checklist
- [ ] Identify assets: authority ceilings, active config, controller state, demand signals, identity tokens, target outputs, release artifacts, evidence, and audit logs.
- [ ] Enumerate trust boundaries and data flows.
- [ ] Model attacker classes: malicious tenant, compromised workload, compromised operator credential, malicious dependency, compromised build runner, network attacker, compromised provider, insider, and stale controller instance.
- [ ] Use a consistent method such as STRIDE/LINDDUN/attack trees and record applicability.
- [ ] Analyze spoofing of demand sources and limit authorities.
- [ ] Analyze tampering with package artifacts, configs, schemas, evidence, and dependency downloads.
- [ ] Analyze replay/rollback to vulnerable or stale package/config versions.
- [ ] Analyze privilege escalation through admin/freeze/ceiling interfaces.
- [ ] Analyze denial-of-service and resource exhaustion at parsing, queues, retries, telemetry, and coordination layers.
- [ ] Analyze multi-tenant information leakage through metrics/logs/timing.
- [ ] Analyze supply-chain dependency substitution/typosquatting/compromised package risks.
- [ ] Define security invariants and required mitigations for each high-risk threat.
- [ ] Generate an SBOM for every release artifact.
- [ ] Verify artifact digest before installation/activation.
- [ ] Verify trusted signature/provenance/attestation according to the selected release model.
- [ ] Maintain an approved-version policy for PLN-05 and critical dependencies.
- [ ] Reject or quarantine unsigned/unapproved artifacts in production paths.
- [ ] Record verification result in release and runtime evidence.
- [ ] Map threat IDs to security tests in MC-14.
- [ ] Review the threat model after architecture or trust-boundary changes.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] High/critical threats have explicit mitigations and verification coverage.
- [ ] Production artifacts are integrity-verified and provenance-linked before use.
- [ ] SBOM and approved-version evidence is generated per release.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-12 — Isolation and cryptographic data protection
**Recommended priority:** P0 — multi-tenant/data security  
**Objective:** Enforce tenant/workload isolation and protect sensitive data in transit and at rest with managed key rotation and minimized authority.  
**Dependencies:** MC-06 and MC-11.

## Required deliverables
- [ ] `security/isolation-model.md`
- [ ] `security/crypto-policy.md`
- [ ] Runtime isolation configuration
- [ ] Isolation and crypto conformance tests

## Component-specific implementation checklist
- [ ] Define isolation domains for tenant, workload, site, process/container/VM, state store, metrics, and audit data.
- [ ] Define whether one controller instance may handle multiple tenants and the exact memory/state separation model if so.
- [ ] Prevent tenant-controlled identifiers from selecting another tenant's state.
- [ ] Enforce authorization scope at every state lookup and target publication boundary.
- [ ] Define process/container/VM sandbox requirements and forbidden ambient capabilities.
- [ ] Minimize filesystem, network, device, and credential authority.
- [ ] Require authenticated encryption for network transport where data crosses trust boundaries.
- [ ] Define accepted TLS/mTLS versions, cipher policy, certificate validation, hostname/workload identity validation, and revocation behavior.
- [ ] Define encryption-at-rest requirements for durable state, config snapshots, credentials, and audit records.
- [ ] Define key ownership, KMS/HSM integration, key hierarchy, and tenant/site separation where applicable.
- [ ] Define key rotation cadence and overlapping-key transition procedure.
- [ ] Define behavior when keys are expired, revoked, unavailable, or fail integrity checks.
- [ ] Prevent secrets/keys from appearing in logs, traces, metrics labels, crash dumps, or evidence bundles.
- [ ] Define secure zeroization expectations for in-memory secret material where feasible.
- [ ] Add cross-tenant negative tests.
- [ ] Add certificate/key rotation and expiry tests.
- [ ] Add downgrade-prevention tests for transport/security protocol versions.
- [ ] Document cryptographic agility and migration procedure.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Cross-tenant reads/writes/target effects are prevented and tested.
- [ ] All protected transport/storage paths use approved cryptographic mechanisms.
- [ ] Key rotation and revocation are operationally testable without unsafe control behavior.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-13 — Security-service outage and tamper-evident audit subsystem
**Recommended priority:** P0 — fail-safe security operations  
**Objective:** Define safe behavior when identity, attestation, policy, key, or trusted-time services fail and produce durable tamper-evident audit events for security-sensitive actions.  
**Dependencies:** MC-06, MC-10, MC-11, MC-12.

## Required deliverables
- [ ] `security/security_dependency_failure_policy.md`
- [ ] Audit event schema
- [ ] Append-only/tamper-evident audit implementation
- [ ] Outage and audit-integrity tests

## Component-specific implementation checklist
- [ ] Enumerate security dependencies: identity provider, certificate authority, policy engine, attestation service, KMS/HSM, trusted time, revocation source.
- [ ] Classify each dependency as fail-closed, bounded fail-static, cached-grace, or noncritical.
- [ ] Define maximum cache age for identity/policy/key material.
- [ ] Define behavior when trusted time is unavailable or skew exceeds tolerance.
- [ ] Prevent a security-service outage from implicitly expanding authority.
- [ ] Define safe ceiling/floor behavior during authorization uncertainty.
- [ ] Define when the controller must freeze, degrade, quarantine, or stop publishing targets.
- [ ] Emit audit events for authentication failures, authorization denials, config changes, limit changes, freeze/unfreeze, quarantine, artifact verification, key rotation, and break-glass use.
- [ ] Define stable audit event IDs, actor identity, tenant/site scope, timestamp, correlation ID, action, result, reason, and object revision.
- [ ] Use append-only storage or cryptographic chaining/signing appropriate to the deployment environment.
- [ ] Detect gaps, truncation, reordering, or tampering in audit sequences.
- [ ] Define local buffering when the remote audit sink is unavailable.
- [ ] Bound audit buffers and define fail behavior if they fill.
- [ ] Protect audit confidentiality while preserving integrity.
- [ ] Define retention, access, export, and legal/privacy constraints.
- [ ] Add tests for identity outage, policy outage, key outage, time outage, sink outage, and audit tampering.
- [ ] Ensure security-sensitive operations are never silently omitted from audit.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Loss of a security dependency never grants additional authority.
- [ ] Security-sensitive actions are attributable and tamper-detectable.
- [ ] Audit sink outages have bounded, deterministic behavior.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-14 — Adversarial security test suite
**Recommended priority:** P1 — security verification  
**Objective:** Translate the threat model into repeatable automated adversarial tests covering privilege escalation, injection, replay, spoofing, isolation escape, side channels, and resource exhaustion.  
**Dependencies:** MC-11 through MC-13.

## Required deliverables
- [ ] `tests/security/`
- [ ] Threat-to-test mapping
- [ ] Security test corpus
- [ ] Machine-readable security test report

## Component-specific implementation checklist
- [ ] Create one or more test cases for every high/critical threat ID.
- [ ] Attempt unauthorized ceiling increases and floor decreases.
- [ ] Attempt demand-source spoofing and identity confusion.
- [ ] Attempt cross-tenant and cross-site state access.
- [ ] Replay previously valid demand/config/control requests.
- [ ] Reorder and duplicate signed/control messages.
- [ ] Inject malformed structured data, oversized values, deeply nested structures, and encoding edge cases.
- [ ] Test parser and schema behavior for NaN/Infinity/extreme integers where formats permit.
- [ ] Test command/template/path/log injection surfaces if present.
- [ ] Attempt privilege escalation from read-only to control/admin operations.
- [ ] Attempt use of expired/revoked credentials and stale policies.
- [ ] Test certificate downgrade and wrong-identity acceptance.
- [ ] Test unsigned/tampered package/config/evidence artifacts.
- [ ] Exercise dependency-confusion/unsupported dependency version rejection.
- [ ] Drive request rates, queue sizes, telemetry labels, and error generation to exhaustion thresholds.
- [ ] Test retry amplification under attacker-controlled failures.
- [ ] Test timing/cardinality behavior for obvious tenant-information leakage.
- [ ] Test quarantine/freeze controls against unauthorized bypass.
- [ ] Run security tests under optimized runtime modes where assertions may differ.
- [ ] Integrate failures into CI release-blocking policy according to severity.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every high/critical threat has an automated or explicitly justified manual verification.
- [ ] Security regressions fail CI/release gates.
- [ ] Test results are machine-readable and included in acceptance evidence.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-15 — Failure matrix and health / stall detection
**Recommended priority:** P0 — resilience foundation  
**Objective:** Enumerate failure modes across process, VM/container, node, site, network, provider, dependency, and control plane, then detect unhealthy/stalled behavior with deterministic thresholds.  
**Dependencies:** MC-03, MC-24.

## Required deliverables
- [ ] `reliability/failure_matrix.yaml`
- [ ] Health/stall detector implementation
- [ ] Detector thresholds/config schema
- [ ] Failure-detection tests

## Component-specific implementation checklist
- [ ] Enumerate process crash, exception loop, deadlock, livelock, event-loop stall, and resource exhaustion.
- [ ] Enumerate container/VM restart, eviction, freeze, clock pause, and disk-full conditions.
- [ ] Enumerate node loss, node overload, local network loss, and DNS/service-discovery failure.
- [ ] Enumerate site isolation and multi-site partition scenarios.
- [ ] Enumerate provider API outage, throttling, partial success, stale inventory, and delayed acknowledgements.
- [ ] Enumerate demand-source outage, stale signal, malformed signal, and contradictory sources.
- [ ] Enumerate policy/IAM/KMS/time/telemetry/coordination service failures.
- [ ] Define observable symptoms and detection signal for each failure.
- [ ] Define detection threshold, debounce, hysteresis, and maximum detection time.
- [ ] Differentiate **healthy**, **degraded**, **unready**, **stalled**, and **failed**.
- [ ] Use monotonic time for local stall timing.
- [ ] Define heartbeat semantics and avoid heartbeat-only false health.
- [ ] Detect progress, not merely process liveness, for long-running workflows.
- [ ] Define how health state influences readiness and decision publication.
- [ ] Define alert severity per failure mode.
- [ ] Add unit tests for threshold boundaries.
- [ ] Add integration tests for recovery and flapping conditions.
- [ ] Document known undetectable failures and compensating controls.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every material failure class has a defined detection mechanism or documented limitation.
- [ ] Stall detection has bounded detection time and false-positive controls.
- [ ] Health state deterministically affects readiness/operation.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-16 — Retry / admission control / circuit-breaker layer
**Recommended priority:** P0 — overload safety  
**Objective:** Provide bounded retries with backoff/jitter plus admission control, load shedding, and circuit breakers so dependency failures or bursts cannot cause retry storms or unbounded resource growth.  
**Dependencies:** MC-07, MC-15.

## Required deliverables
- [ ] `reliability/retry_policy.*`
- [ ] `reliability/admission.py` / equivalent
- [ ] Circuit-breaker state machine
- [ ] Overload tests and metrics

## Component-specific implementation checklist
- [ ] Define retry eligibility per operation/error code.
- [ ] Define maximum attempts and total retry deadline.
- [ ] Use exponential or decorrelated backoff with bounded jitter.
- [ ] Cap retry concurrency and retry budget globally/per dependency.
- [ ] Ensure idempotency before enabling retries.
- [ ] Propagate cancellation and deadline budgets across retries.
- [ ] Stop retries when the source input becomes stale or superseded.
- [ ] Define admission limits by queue depth, concurrency, CPU/memory pressure, or token budget.
- [ ] Reject early before expensive parsing/work when capacity is unavailable.
- [ ] Define load-shedding priority classes; protect safety/control operations from low-priority telemetry/reporting load.
- [ ] Implement bounded queues with explicit overflow behavior.
- [ ] Implement circuit-breaker closed/open/half-open transitions.
- [ ] Define breaker thresholds for consecutive failures, error rate, latency, and timeout.
- [ ] Prevent synchronized half-open probes across replicas.
- [ ] Expose retry, rejection, shed, and breaker metrics.
- [ ] Define dependency-specific breaker isolation so one failed provider does not disable unrelated operations.
- [ ] Test retry storms, slow dependencies, intermittent failures, and recovery.
- [ ] Verify overload behavior does not raise authority or lose critical audit events.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Retries and queues have hard bounds.
- [ ] Dependency failure cannot create unbounded amplification.
- [ ] Admission/load shedding preserves critical control-path responsiveness.
- [ ] Circuit breaker recovery is deterministic and observable.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-17 — Failover and degraded-operation controller
**Recommended priority:** P0 — availability/safety  
**Objective:** Define and implement safe failover and degraded modes that preserve residency/isolation constraints and handle stale demand or noncritical dependency loss without unsafe scaling.  
**Dependencies:** MC-03, MC-06, MC-10, MC-15, MC-16, MC-18.

## Required deliverables
- [ ] `reliability/degraded_modes.md`
- [ ] Failover policy/configuration
- [ ] Degraded-mode state machine
- [ ] Failover integration tests

## Component-specific implementation checklist
- [ ] Enumerate failover-eligible dependencies and state which are not safely failoverable.
- [ ] Define alternate demand source behavior, including trust rank and freshness.
- [ ] Define alternate provider/control-plane behavior if multiple providers/regions exist.
- [ ] Preserve tenant residency, sovereignty, and site constraints during failover.
- [ ] Preserve security/isolation capabilities during failover; never fail open to weaker trust.
- [ ] Define stale-demand thresholds and target behavior by stale duration.
- [ ] Define whether last-known-good demand/target may be reused and for how long.
- [ ] Define maximum authority in degraded mode, potentially stricter than normal ceiling.
- [ ] Define behavior when capacity confirmation is unavailable.
- [ ] Define behavior when telemetry is unavailable but control path remains healthy.
- [ ] Define operator-visible degraded reasons and transition timestamps.
- [ ] Require explicit criteria to exit degraded mode.
- [ ] Debounce dependency flapping to prevent rapid failover/failback oscillation.
- [ ] Coordinate failover with leader/fencing state to prevent dual active controllers.
- [ ] Define rollback if failover target/provider rejects or partially applies an action.
- [ ] Test site partition, dependency outage, stale demand, recovery, and failback.
- [ ] Test that failover never violates residency/isolation constraints.
- [ ] Document operator actions for prolonged degraded operation.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Every supported degraded mode has deterministic entry/exit criteria.
- [ ] Failover cannot weaken tenant/security/residency constraints.
- [ ] Stale-demand behavior is bounded and independently testable.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-18 — Durable controller state and distributed coordination
**Recommended priority:** P0 — correctness under restart/replication  
**Objective:** Persist controller state crash-consistently and coordinate replicated ownership with leases/epochs/fencing to prevent stale or duplicate controllers from publishing authority.  
**Dependencies:** MC-03, MC-10, MC-15.

## Required deliverables
- [ ] `state/state_schema.*`
- [ ] Durable state adapter
- [ ] Lease/epoch/fencing implementation
- [ ] Crash/replay/split-brain tests

## Component-specific implementation checklist
- [ ] Enumerate state that must survive restart: current target, pending direction/count, active config revision, authority envelope, last accepted input metadata, freeze/quarantine state as applicable.
- [ ] Separate reconstructible state from must-persist state.
- [ ] Define a versioned durable state schema.
- [ ] Use atomic write/transaction semantics so partially written state is never accepted.
- [ ] Persist checksum/integrity metadata.
- [ ] Define fsync/durability requirements appropriate to deployment tier.
- [ ] Define startup recovery order and validation.
- [ ] Reject state from unsupported future versions.
- [ ] Provide migration path for older state versions.
- [ ] Define replay semantics and whether previously emitted targets may be re-emitted.
- [ ] Use idempotent output identifiers to avoid duplicate side effects after restart.
- [ ] Define active-controller ownership using lease/epoch/term semantics.
- [ ] Use fencing tokens on downstream target application where possible.
- [ ] Ensure a controller that loses lease immediately loses publication authority.
- [ ] Prevent split-brain publication after partitions.
- [ ] Define lease duration, renewal deadline, clock assumptions, and failure behavior.
- [ ] Persist/compare epoch with controller state to detect stale resurrection.
- [ ] Test crash at every persistence boundary.
- [ ] Test restart, duplicate process, lease loss, network partition, stale leader, and state corruption.
- [ ] Expose state schema/epoch/owner status in health/explain surfaces.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Restart does not silently reset behavior in a way that violates hysteresis/safety semantics.
- [ ] At most one authorized controller can publish for a given ownership scope.
- [ ] Stale instances are fenced from downstream effects.
- [ ] State corruption fails safe and is observable.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-19 — Runtime quarantine / freeze / disable controls
**Recommended priority:** P0 — emergency safety  
**Objective:** Provide authorized runtime controls to stop or constrain unsafe elasticity decisions without uninstalling the component.  
**Dependencies:** MC-06, MC-10, MC-13, MC-18, MC-24.

## Required deliverables
- [ ] Administrative control API/CLI
- [ ] Freeze/quarantine state schema
- [ ] Runbook for emergency controls
- [ ] Authorization/audit tests

## Component-specific implementation checklist
- [ ] Define distinct semantics for **freeze**, **disable**, **quarantine**, **drain**, and **resume**.
- [ ] Specify whether freeze holds current target, forces a safe target, or blocks publication only.
- [ ] Specify quarantine behavior for untrusted input/source vs whole-controller quarantine.
- [ ] Make controls scoped by tenant/workload/site rather than global-only when architecture requires.
- [ ] Require a dedicated privileged capability.
- [ ] Require reason, actor, ticket/incident reference, and optional expiry for emergency actions.
- [ ] Persist control state across restart if safety requires it.
- [ ] Ensure emergency state participates in leader/fencing semantics.
- [ ] Define precedence over ordinary demand/config updates.
- [ ] Prevent lower-privilege config updates from clearing emergency controls.
- [ ] Provide dry-run/status visibility before operator action.
- [ ] Emit tamper-evident audit records.
- [ ] Expose active freeze/quarantine state in health/readiness/explain surfaces.
- [ ] Define automatic expiry only where safe; avoid accidental silent unfreeze.
- [ ] Provide explicit two-step or approval workflow for especially dangerous resume/override actions if warranted.
- [ ] Test control application during normal operation, dependency outage, partition, restart, and failover.
- [ ] Test unauthorized bypass attempts.
- [ ] Document recovery procedure and validation before resuming.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Operators can stop unsafe decision publication without package removal.
- [ ] Emergency controls survive the required failure/restart scenarios.
- [ ] Only authorized actors can apply/clear controls and every action is auditable.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-20 — Fault-injection / disaster test harness
**Recommended priority:** P1 — resilience verification  
**Objective:** Build repeatable fault injection for process, node, site, network, provider, dependency, partition/reconnect, and degraded-control-plane scenarios.  
**Dependencies:** MC-15 through MC-19.

## Required deliverables
- [ ] `tests/fault/`
- [ ] Fault scenario manifest
- [ ] Local/CI chaos harness
- [ ] Recovery evidence reports

## Component-specific implementation checklist
- [ ] Create a catalog of fault scenarios mapped to MC-15 failure IDs.
- [ ] Support deterministic process crash and kill injection.
- [ ] Support forced exception/error responses at dependency boundaries.
- [ ] Support latency, timeout, packet loss, connection reset, DNS failure, and bandwidth constraints.
- [ ] Support message duplication, reordering, delay, and replay where protocol permits.
- [ ] Support disk-full, read-only storage, corrupted state, and partial persistence failures.
- [ ] Support clock skew/jump simulation for time-dependent logic.
- [ ] Support lease-store/coordination outage and stale leader scenarios.
- [ ] Support identity/policy/KMS/time-service outage scenarios.
- [ ] Support provider throttling, partial success, and stale responses.
- [ ] Support demand-source silence, stale data, malformed data, and contradictory inputs.
- [ ] Support whole-site isolation and reconnect.
- [ ] Define preconditions, injection point, expected behavior, maximum detection time, maximum recovery time, and invariants for each scenario.
- [ ] Automate cleanup and environment reset.
- [ ] Seed randomized faults reproducibly.
- [ ] Capture logs/metrics/traces/state snapshots with correlation IDs.
- [ ] Verify no authority ceiling/security invariant is violated during faults.
- [ ] Run a production-like disaster suite before release and a reduced suite in CI.
- [ ] Store machine-readable results in the acceptance bundle.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Critical failure modes are exercised, not only documented.
- [ ] Recovery behavior and invariant preservation are automatically asserted.
- [ ] Fault runs are reproducible and evidence-producing.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-21 — Performance baseline and load-test suite
**Recommended priority:** P1 — capacity certification  
**Objective:** Establish reproducible performance baselines for latency, throughput, startup, CPU, memory, storage, network, and power where relevant under steady, burst, overload, scale, and recovery workloads.  
**Dependencies:** MC-03, MC-09, MC-24, MC-25.

## Required deliverables
- [ ] `benchmarks/`
- [ ] Workload profiles
- [ ] Baseline result files
- [ ] Benchmark environment manifest

## Component-specific implementation checklist
- [ ] Define benchmark hardware/runtime profiles and capture CPU, memory, OS, Python/runtime, container/VM, and dependency versions.
- [ ] Define warm and cold startup benchmarks.
- [ ] Measure observe/decision latency p50/p95/p99/max.
- [ ] Measure sustained decision throughput.
- [ ] Measure CPU time per decision and under sustained load.
- [ ] Measure resident memory baseline, peak, and growth over time.
- [ ] Measure allocation/GC behavior if relevant.
- [ ] Measure serialized request/response size and network bandwidth where remote interfaces exist.
- [ ] Measure durable-state read/write latency once MC-18 exists.
- [ ] Measure control path under steady load.
- [ ] Measure burst response and queue/backpressure behavior.
- [ ] Measure overload behavior to and beyond configured admission limits.
- [ ] Measure recovery after overload clears.
- [ ] Measure scaling with tenant/workload cardinality and controller-instance count.
- [ ] Measure impact of observability enabled vs disabled/sampled.
- [ ] Measure impact of security verification/signature/IAM paths.
- [ ] Measure edge power/thermal behavior for supported edge profiles where required.
- [ ] Use fixed datasets/seeds and store benchmark parameters with results.
- [ ] Run repeated trials and report variance/confidence, not one-off numbers.
- [ ] Define pass/fail SLO thresholds from MC-03.
- [ ] Export machine-readable benchmark results for MC-23.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Baselines are reproducible on declared reference environments.
- [ ] All NFR latency/throughput/resource budgets have corresponding measurements.
- [ ] Steady, burst, overload, scale, and recovery profiles are represented.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-22 — Efficiency / resource-bounds analysis
**Recommended priority:** P1 — scalability / edge fitness  
**Objective:** Quantify serialization, copies, context switches, network hops, state duplication, queue/concurrency/fan-out bounds, and optimization opportunities, including edge power/thermal impact.  
**Dependencies:** MC-21.

## Required deliverables
- [ ] `performance/efficiency-analysis.md`
- [ ] Resource-bound formulas/configuration
- [ ] Profiling artifacts
- [ ] Optimization decision records

## Component-specific implementation checklist
- [ ] Map the end-to-end decision data path from demand source to target consumer.
- [ ] Count serialization/deserialization operations per decision.
- [ ] Count memory copies where observable.
- [ ] Count process/thread/context-switch boundaries.
- [ ] Count network hops and RPCs per decision.
- [ ] Identify duplicated state across replicas/components.
- [ ] Measure payload sizes and compression trade-offs if applicable.
- [ ] Profile CPU hotspots under representative load.
- [ ] Profile memory allocations and long-lived object retention.
- [ ] Define hard bounds for inbound queues.
- [ ] Define hard bounds for retry queues.
- [ ] Define hard bounds for concurrent requests/decisions.
- [ ] Define fan-out bounds to providers/peers/telemetry sinks.
- [ ] Prove that bound multiplication cannot exceed memory/CPU safety budgets.
- [ ] Evaluate locality/caching opportunities and stale-cache risks.
- [ ] Evaluate batching/coalescing opportunities without violating reaction SLOs.
- [ ] Evaluate zero-copy/kernel-bypass only where measurement shows material benefit; document rejection if not justified.
- [ ] Measure observability cardinality/resource impact.
- [ ] Measure cryptographic verification overhead.
- [ ] Measure edge power draw and thermal throttling where edge is supported.
- [ ] Record optimization changes with before/after benchmark evidence.
- [ ] Ensure optimizations preserve deterministic semantics and security boundaries.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Resource consumption has explicit calculable bounds.
- [ ] Major copies/hops/queues/fan-out are measured and justified.
- [ ] Optimizations are evidence-based and regression-tested.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-23 — Performance regression release gate
**Recommended priority:** P1 — release quality gate  
**Objective:** Automatically compare current performance against approved baselines and block releases that exceed startup, density, throughput, resource, or tail-latency thresholds.  
**Dependencies:** MC-21 and MC-22; integrates with MC-33.

## Required deliverables
- [ ] `ci/performance_gate.*`
- [ ] Baseline registry
- [ ] Threshold policy
- [ ] Machine-readable gate result

## Component-specific implementation checklist
- [ ] Select benchmark scenarios that are stable enough for automated gating.
- [ ] Define absolute SLO thresholds and relative regression thresholds separately.
- [ ] Gate p95/p99 latency, not averages only.
- [ ] Gate throughput at fixed resource allocation.
- [ ] Gate startup latency.
- [ ] Gate peak and steady-state memory.
- [ ] Gate CPU per operation or CPU at fixed throughput.
- [ ] Gate queue saturation/overload recovery where measurable.
- [ ] Define platform-specific baselines for materially different architectures.
- [ ] Use repeated samples and statistical tolerance to reduce flaky decisions.
- [ ] Define allowed variance and minimum sample count.
- [ ] Normalize or pin noisy CI host variables where feasible.
- [ ] Version baselines and tie them to release/environment metadata.
- [ ] Require explicit approved baseline update rather than silently accepting regressions.
- [ ] Record who/why when a threshold is waived.
- [ ] Expire performance waivers.
- [ ] Emit machine-readable pass/fail and individual metric deltas.
- [ ] Attach result to the production acceptance bundle.
- [ ] Run a smaller presubmit gate and fuller release benchmark gate if cost requires.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] A material performance regression cannot be released silently.
- [ ] Baseline changes are reviewed and auditable.
- [ ] Gate output is deterministic enough to support release automation.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-24 — Runtime health / readiness / status surface
**Recommended priority:** P0 — operability  
**Objective:** Expose machine-readable liveness, readiness, version, active configuration, dependency status, authority state, and active capabilities without leaking sensitive data.  
**Dependencies:** MC-03, MC-10, MC-15, MC-18, MC-19.

## Required deliverables
- [ ] Health/readiness API or CLI
- [ ] Status schema
- [ ] Status redaction policy
- [ ] Health conformance tests

## Component-specific implementation checklist
- [ ] Separate liveness from readiness.
- [ ] Define readiness blockers: invalid config, lost ownership/lease, stale critical input, failed security dependency, corrupted state, quarantine, or unsupported schema.
- [ ] Expose package/runtime version and build identifier.
- [ ] Expose active configuration schema version and checksum/revision.
- [ ] Expose current ownership scope, lease/epoch status, and fencing state without disclosing secrets.
- [ ] Expose current floor/ceiling/target and controller mode where safe.
- [ ] Expose dependency health with stable dependency IDs.
- [ ] Expose active degraded/freeze/quarantine states and reasons.
- [ ] Expose supported schema/capability versions.
- [ ] Expose last successful decision timestamp and last accepted demand age.
- [ ] Expose last failure/error category in a bounded/redacted form.
- [ ] Define health query timeout and ensure it cannot block on unhealthy downstream dependencies.
- [ ] Keep health/status path lightweight and bounded under overload.
- [ ] Protect sensitive administrative detail behind appropriate authorization.
- [ ] Provide a local diagnostic path when network APIs are unavailable.
- [ ] Add status schema versioning.
- [ ] Test each unhealthy/degraded transition.
- [ ] Test redaction and unauthorized access.
- [ ] Integrate readiness with deployment orchestrator probes where applicable.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Automation can distinguish alive, ready, degraded, frozen, quarantined, and failed states.
- [ ] Status reflects the active config/dependency/ownership state used for decisions.
- [ ] Health endpoints remain bounded and safe during dependency failure.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-25 — Metrics / structured logging / tracing implementation
**Recommended priority:** P0 — observability core  
**Objective:** Implement stable metrics, structured logs, and trace-context propagation with safe cardinality, redaction, and correlation across decision and dependency boundaries.  
**Dependencies:** MC-03, MC-24; feeds MC-26 and MC-27.

## Required deliverables
- [ ] Metrics registry/emitter
- [ ] Structured logging configuration/schema
- [ ] Tracing instrumentation
- [ ] Observability tests

## Component-specific implementation checklist
- [ ] Define a stable service/component identity and version attribute set.
- [ ] Emit decision counters by outcome class.
- [ ] Emit decision latency histogram with approved buckets.
- [ ] Emit input age/staleness metrics.
- [ ] Emit current target/floor/ceiling gauges where safe and useful.
- [ ] Emit queue depth, concurrency, retry, rejection, load-shed, and circuit-breaker metrics once MC-16 exists.
- [ ] Emit lease/leadership/fencing metrics once MC-18 exists.
- [ ] Emit dependency health and error counters.
- [ ] Use structured logs rather than free-form strings for operational events.
- [ ] Include stable correlation/request/operation IDs.
- [ ] Include tenant/workload/site identifiers only when cardinality/privacy policy permits.
- [ ] Define severity levels consistently.
- [ ] Redact secrets, tokens, keys, raw sensitive payloads, and excessive PII.
- [ ] Propagate W3C Trace Context or the selected standard across supported boundaries.
- [ ] Create spans for boundary validation, policy/IAM checks, state access, decision calculation, and target publication as appropriate.
- [ ] Set span attributes with bounded cardinality.
- [ ] Define sampling behavior and error/rare-event retention.
- [ ] Ensure observability failure cannot block safety-critical decision logic.
- [ ] Test redaction with representative secret patterns.
- [ ] Test metric cardinality under high tenant/workload counts.
- [ ] Test trace continuity across adjacent-layer integration fixtures.
- [ ] Version/log schema changes where downstream parsing depends on them.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Operators can correlate an input to a decision and downstream publication using stable IDs.
- [ ] Observability is bounded, redacted, and non-blocking.
- [ ] Core SLO/error/saturation signals are emitted programmatically, not only documented.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-26 — Explainability / correlation layer
**Recommended priority:** P1 — operator diagnosis  
**Objective:** Provide an operator explain view that reconstructs why a decision occurred from input, policy, configuration, constraints, topology, ownership, and release lineage.  
**Dependencies:** MC-10, MC-18, MC-24, MC-25.

## Required deliverables
- [ ] Explain API/CLI
- [ ] Decision provenance schema
- [ ] Correlation store/index
- [ ] Explainability tests

## Component-specific implementation checklist
- [ ] Assign a unique decision ID to every decision cycle/result.
- [ ] Record the exact accepted demand observation ID/version.
- [ ] Record active config revision/checksum.
- [ ] Record policy/IAM decision reference when authorization or policy affects the result.
- [ ] Record active floor/ceiling and their provenance/authority source.
- [ ] Record current capacity, pending hysteresis state, and relevant prior target.
- [ ] Record degraded/freeze/quarantine state influencing the decision.
- [ ] Record ownership epoch/lease/fencing token reference.
- [ ] Record dependency/topology snapshot references when they constrain action.
- [ ] Record the chosen outcome and structured reason code, not prose only.
- [ ] Record rejected alternative reasons where useful, e.g. requested scale-up but ceiling constrained.
- [ ] Record package version/build/provenance.
- [ ] Record infrastructure/provider release/adapter versions affecting publication.
- [ ] Provide lookup by decision ID, correlation ID, workload/tenant, and time window subject to privacy policy.
- [ ] Bound retention and storage size.
- [ ] Redact sensitive identity/config values.
- [ ] Make explain output deterministic enough for automated assertions.
- [ ] Add tests for scale-up, scale-down, floor hold, ceiling hold, stale input, freeze, degraded, and authorization-constrained cases.
- [ ] Ensure explain data cannot be altered without corresponding audit/provenance evidence where high assurance is required.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] An operator can answer 'why did PLN-05 choose this target?' without reconstructing state from unrelated logs.
- [ ] Explain output identifies the exact config/policy/release/ownership context.
- [ ] Sensitive data remains redacted and access-controlled.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-27 — Telemetry policy, dashboards, and alerts
**Recommended priority:** P1 — operations visibility  
**Objective:** Define telemetry retention/sampling/privacy/export policy and provide actionable dashboards and alert rules tied to SLOs, saturation, security, and degraded operation.  
**Dependencies:** MC-25; references MC-03 SLOs.

## Required deliverables
- [ ] `observability/telemetry-policy.md`
- [ ] Dashboard definitions
- [ ] Alert rule definitions
- [ ] Alert runbook links

## Component-specific implementation checklist
- [ ] Classify metrics, logs, traces, audit events, and explain records by sensitivity.
- [ ] Define retention periods for each telemetry class.
- [ ] Define sampling policy for traces and high-volume logs.
- [ ] Define export destinations and transport security.
- [ ] Define tenant/site data-separation requirements in telemetry backends.
- [ ] Define label/tag allowlist to control cardinality.
- [ ] Define redaction and deletion requirements.
- [ ] Create dashboard for decision rate/outcome distribution.
- [ ] Create dashboard for reaction latency p50/p95/p99 and SLO compliance.
- [ ] Create dashboard for stale demand/input quality.
- [ ] Create dashboard for floor/ceiling constrained decisions.
- [ ] Create dashboard for queue/retry/load-shed/circuit-breaker state.
- [ ] Create dashboard for leader/lease/fencing health.
- [ ] Create dashboard for degraded/freeze/quarantine state.
- [ ] Create dependency health dashboard.
- [ ] Create alerts for readiness loss, sustained decision failure, stale critical input, lease loss, audit buffer pressure, excessive retries, persistent ceiling/floor constraint, and SLO burn.
- [ ] Use multi-window/multi-burn-rate SLO alerts where appropriate.
- [ ] Set alert severity and ownership/escalation route.
- [ ] Include runbook links in alert annotations.
- [ ] Test alert expressions against synthetic scenarios.
- [ ] Review alerts for noise and define tuning/change process.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Dashboards expose the signals required to operate the controller without ad-hoc log searches.
- [ ] Alerts are actionable, routed, and tied to documented runbooks.
- [ ] Telemetry retention/export is privacy- and cardinality-controlled.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-28 — Compatibility / fuzz / concurrency test matrix
**Recommended priority:** P1 — robustness  
**Objective:** Validate supported CPU/runtime/hypervisor/provider/protocol combinations and expose parser/state-machine/race defects through fuzzing, property testing, and concurrency testing.  
**Dependencies:** MC-05, MC-07, MC-09, MC-18.

## Required deliverables
- [ ] `tests/compatibility/`
- [ ] `tests/fuzz/`
- [ ] `tests/concurrency/`
- [ ] Supported compatibility matrix

## Component-specific implementation checklist
- [ ] Define supported CPU architectures and minimum features.
- [ ] Define supported OS/runtime/Python versions.
- [ ] Define supported container/VM/hypervisor tiers if relevant.
- [ ] Define supported provider/adapter versions.
- [ ] Define supported schema/protocol version combinations.
- [ ] Test minimum and maximum supported dependency versions.
- [ ] Test upgrade/downgrade compatibility across at least the supported release window.
- [ ] Create property tests for controller invariants: target remains within floor/ceiling, invalid input rejected, hysteresis transitions bounded, lower ceiling never raises authority, etc.
- [ ] Fuzz schema parsers and boundary validators with malformed bytes/objects.
- [ ] Fuzz numeric edge cases and deeply nested/large payload limits.
- [ ] Fuzz state migration/deserialization once durable state exists.
- [ ] Fuzz config overlay/merge logic once MC-10 exists.
- [ ] Define the thread-safety/concurrency contract explicitly.
- [ ] Run concurrent observe/config/status/control operations according to the supported model.
- [ ] Use race detectors or deterministic schedulers where the language/runtime permits.
- [ ] Test concurrent leader handoff/lease loss/publication once MC-18 exists.
- [ ] Test cancellation/timeouts during concurrent operations.
- [ ] Run long randomized state-machine sequences against invariants.
- [ ] Record unsupported combinations explicitly so absence of testing is not mistaken for support.
- [ ] Publish compatibility results with releases.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Supported combinations are explicit and continuously tested.
- [ ] Core invariants survive fuzz/property/concurrency testing.
- [ ] Thread-safety expectations are documented and verified.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-29 — Benchmark / soak / burst / fleet-scale test suite
**Recommended priority:** P1 — production scale confidence  
**Objective:** Validate long-duration stability, burst handling, benchmark repeatability, and behavior at realistic fleet/tenant/workload scale.  
**Dependencies:** MC-21, MC-22, MC-25.

## Required deliverables
- [ ] `tests/scale/`
- [ ] Soak/burst/fleet workload generators
- [ ] Long-run result reports
- [ ] Leak/drift detectors

## Component-specific implementation checklist
- [ ] Define a minimum-duration soak profile appropriate to release confidence.
- [ ] Exercise steady decision traffic for the full soak period.
- [ ] Inject realistic periodic bursts.
- [ ] Exercise worst-case boundary oscillation around thresholds.
- [ ] Exercise sustained overload followed by recovery.
- [ ] Exercise high tenant/workload cardinality.
- [ ] Exercise multiple sites/providers if supported.
- [ ] Exercise leader handoff/failover during long runs.
- [ ] Rotate configuration and credentials during soak if supported.
- [ ] Track RSS/heap growth and detect memory leaks.
- [ ] Track file descriptor/socket/thread/task growth.
- [ ] Track queue depth and ensure no monotonic backlog accumulation.
- [ ] Track latency drift over time.
- [ ] Track error-rate drift and retry amplification.
- [ ] Track telemetry cardinality/storage growth.
- [ ] Track durable-state size growth.
- [ ] Exercise periodic dependency failures during soak.
- [ ] Define fleet-scale target numbers for controllers, workloads, tenants, decision rate, and events/sec.
- [ ] Use deterministic workload seeds and archive generator parameters.
- [ ] Produce machine-readable summary plus failure timeline.
- [ ] Compare long-run metrics to MC-21 baselines and MC-23 thresholds.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] No unbounded resource growth appears over the approved soak duration.
- [ ] Burst/overload recovery returns to baseline without manual reset.
- [ ] Fleet-scale targets are demonstrated on declared reference infrastructure.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-30 — Machine-readable production acceptance bundle
**Recommended priority:** P0 — release evidence  
**Objective:** Generate a release-attached evidence bundle containing requirement/gate results, test/benchmark/security evidence, artifact provenance, dependency resolution, and signed/immutable acceptance metadata.  
**Dependencies:** MC-04, MC-09, MC-14, MC-20, MC-23, MC-28, MC-29, MC-33.

## Required deliverables
- [ ] `evidence/<version>/manifest.json`
- [ ] Requirement/gate result files
- [ ] Checksums/signatures/provenance
- [ ] Release acceptance summary

## Component-specific implementation checklist
- [ ] Define a versioned evidence manifest schema.
- [ ] Include package version, commit/source revision, build ID, timestamp, and environment identity.
- [ ] Include artifact digests and provenance/attestation references.
- [ ] Include SBOM reference and dependency lock/resolve evidence.
- [ ] Include requirements traceability snapshot.
- [ ] Include unit/contract/integration test results.
- [ ] Include security test results.
- [ ] Include fault/disaster test results.
- [ ] Include compatibility/fuzz/concurrency results.
- [ ] Include benchmark/performance-gate results.
- [ ] Include soak/fleet results for release-tier certification.
- [ ] Include static analysis/lint/type/security scan results where adopted.
- [ ] Include configuration/schema compatibility checks.
- [ ] Include unresolved waivers with owner and expiry.
- [ ] Include owner/release approver identities/roles.
- [ ] Use stable machine-readable result statuses and reason codes.
- [ ] Ensure skipped tests are distinguished from passed tests.
- [ ] Fail acceptance when a mandatory dependency such as `pk_core` is neither present nor reproducibly resolvable.
- [ ] Checksum the entire evidence bundle.
- [ ] Sign or provenance-attest the final acceptance bundle where release assurance requires it.
- [ ] Store the bundle with the release artifact and make it retrievable by version.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] A release can be accepted/rejected from the evidence bundle without manually reading CI logs.
- [ ] Skipped/unresolved checks cannot masquerade as passes.
- [ ] Evidence is immutable/version-linked and traceable back to source/build.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-31 — Release and operations governance
**Recommended priority:** P0 — production lifecycle  
**Objective:** Define staged rollout, compatibility, vulnerability/EOL policy, state/config backup and migration, executable runbooks, recurring reviews, and waiver/debt governance.  
**Dependencies:** MC-02, MC-09, MC-10, MC-18, MC-24 through MC-30.

## Required deliverables
- [ ] `docs/release-policy.md`
- [ ] `docs/runbooks/`
- [ ] `compatibility/supported-versions.yaml`
- [ ] `governance/waivers.yaml`

## Component-specific implementation checklist
- [ ] Define release channels/environments and promotion order.
- [ ] Define canary scope, duration, success criteria, and automatic/manual abort conditions.
- [ ] Define staged rollout percentages or deployment rings appropriate to the platform.
- [ ] Define rollback trigger thresholds and rollback procedure.
- [ ] Test rollback from the current release to at least the previous supported release.
- [ ] Define schema/config/state forward and backward compatibility window.
- [ ] Publish a supported-version matrix for PLN-05, runtime, `pk_core`, schemas, and critical sibling interfaces.
- [ ] Define patch policy for functional defects.
- [ ] Define vulnerability response SLA by severity.
- [ ] Define end-of-life/deprecation notice period and unsupported-version behavior.
- [ ] Define backup requirements for durable state and configuration.
- [ ] Define restore procedure and RPO/RTO.
- [ ] Define state/config migration and reconstruction procedure.
- [ ] Create day-0 install/bootstrap runbook with prerequisites and verification.
- [ ] Create day-1 operations runbook for routine health/config/monitoring actions.
- [ ] Create day-2 incident/recovery runbooks for common failures.
- [ ] Create incident severity, paging, escalation, containment, recovery, and postmortem process.
- [ ] Schedule recurring access, policy, dependency, configuration, security, architecture, and capacity reviews.
- [ ] Maintain exception/waiver/debt/deprecation register with owner, rationale, risk, compensating control, approval, and expiry.
- [ ] Block release on expired waivers.
- [ ] Define audit cadence for operational docs and execute periodic game days.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Rollout and rollback are staged, measurable, and rehearsed.
- [ ] Supported versions and vulnerability/EOL commitments are explicit.
- [ ] Critical operational procedures are executable from runbooks.
- [ ] Waivers/debt have owners and expirations rather than permanent ambiguity.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-32 — Master prompt / workflow source bundle
**Recommended priority:** P2 — repository completeness  
**Objective:** Restore or replace the missing master prompt/workflow source with a versioned, testable source-of-truth bundle rather than a stale README reference.  
**Dependencies:** MC-01 to avoid encoding the wrong scope.

## Required deliverables
- [ ] `MASTER.md` or intentionally renamed authoritative workflow source
- [ ] `workflows/` supporting templates/prompts
- [ ] Generated-workflow validation
- [ ] README/source-of-truth references

## Component-specific implementation checklist
- [ ] Determine whether the absent `MASTER.md` is required production source, developer workflow documentation, or obsolete historical material.
- [ ] If obsolete, record the deprecation decision and do not recreate misleading content.
- [ ] If required, define the master prompt/workflow's intended consumers and outputs.
- [ ] Make scope statements consistent with MC-01.
- [ ] Break workflow into deterministic phases with explicit inputs, outputs, prerequisites, and failure conditions.
- [ ] Define which steps are human approvals vs automatable checks.
- [ ] Reference requirements IDs and acceptance gates rather than duplicating requirement prose.
- [ ] Reference canonical schemas/configs by path/version.
- [ ] Define repository-safe relative paths; avoid machine-specific paths.
- [ ] Define Windows/Linux command variants if both are supported.
- [ ] Make generated artifacts deterministic or record nondeterministic inputs.
- [ ] Add lint checks for broken file references and missing referenced artifacts.
- [ ] Add version identifier to the workflow source.
- [ ] Add change log or ADR references for major workflow changes.
- [ ] Ensure README points to the actual authoritative file.
- [ ] Test the workflow against a clean checkout and record required external tools.
- [ ] Prevent workflow text from claiming a test/gate passes unless machine evidence exists.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] No README or workflow reference points to a nonexistent source.
- [ ] The master workflow is either intentionally retired or reproducibly usable from the repository.
- [ ] Workflow steps reference the same authoritative scope and gates as the production spec.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-33 — CI and release automation
**Recommended priority:** P0 — continuous verification  
**Objective:** Automate standalone/framework tests, static checks, packaging, dependency resolution, security scans, evidence generation, performance gates, and release publication.  
**Dependencies:** MC-09; progressively integrates MC-04 through MC-31.

## Required deliverables
- [ ] `.github/workflows/ci.yml` or equivalent CI definition
- [ ] Release workflow
- [ ] Reusable local CI script
- [ ] CI evidence artifacts

## Component-specific implementation checklist
- [ ] Run repository metadata/version consistency checks.
- [ ] Run Python compile/import checks.
- [ ] Run standalone controller tests on every change.
- [ ] Run `pk_core`/framework conformance tests with a reproducibly installed compatible framework.
- [ ] Fail if framework tests are unexpectedly skipped in release jobs.
- [ ] Run schema validation and compatibility checks.
- [ ] Run formatting/linting/type checks if adopted.
- [ ] Run dependency lock/resolve verification.
- [ ] Run dependency vulnerability and license-policy scans.
- [ ] Run unit/contract/integration/security/fuzz test tiers at appropriate cadence.
- [ ] Run package build and clean-environment install test.
- [ ] Run artifact integrity/SBOM/provenance generation.
- [ ] Run performance smoke/regression gate.
- [ ] Run selected fault tests in presubmit and full fault suite in release/nightly jobs.
- [ ] Run traceability validation and waiver-expiry checks.
- [ ] Generate the machine-readable acceptance bundle.
- [ ] Use least-privilege CI credentials and protected release environments.
- [ ] Pin third-party CI actions/tools by immutable version/digest where supported.
- [ ] Prevent untrusted pull-request code from accessing release secrets.
- [ ] Sign/attest release artifacts according to MC-11.
- [ ] Publish checksum/evidence alongside release artifact.
- [ ] Provide an equivalent local command so CI logic is not opaque/vendor-only.
- [ ] Cache dependencies safely without permitting stale/poisoned artifact substitution.
- [ ] Define branch/tag protection and required checks for release.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] A clean CI runner can reproduce build/test/package/evidence from source.
- [ ] Release jobs cannot report success when mandatory tests are skipped.
- [ ] Artifacts and evidence are generated from the same immutable source revision.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-34 — License / security / release metadata
**Recommended priority:** P0 — distribution governance  
**Objective:** Add the legal, security-reporting, ownership, release, and vulnerability-intake metadata required for a distributable and supportable production repository.  
**Dependencies:** MC-02 and organizational policy.

## Required deliverables
- [ ] `LICENSE`
- [ ] `NOTICE` if required
- [ ] `SECURITY.md`
- [ ] `CODEOWNERS` and release/support metadata

## Component-specific implementation checklist
- [ ] Select and add the authoritative software license approved for distribution.
- [ ] Ensure package metadata and README identify the same license.
- [ ] Add NOTICE/attribution file where dependencies/license obligations require it.
- [ ] Inventory third-party dependency licenses and flag incompatible/restricted licenses.
- [ ] Document source and binary redistribution obligations.
- [ ] Create `SECURITY.md` with supported versions.
- [ ] Document private vulnerability reporting channel/process without encouraging public disclosure of unpatched vulnerabilities.
- [ ] Define expected acknowledgement and remediation timelines by severity or reference organizational policy.
- [ ] Document coordinated disclosure expectations.
- [ ] Define how security advisories map to patched releases.
- [ ] Add `CODEOWNERS` or equivalent ownership metadata aligned with MC-02.
- [ ] Add release/versioning policy, including semantic versioning rules or chosen alternative.
- [ ] Add changelog/release-note policy.
- [ ] Define deprecation/EOL signaling in metadata.
- [ ] Add repository metadata for issue templates/bug reports if appropriate.
- [ ] Add machine-readable project metadata where ecosystem tooling benefits.
- [ ] Ensure release artifacts include license/notice files.
- [ ] Add CI check that required governance files exist and package metadata matches them.
- [ ] Review all names/trademarks/third-party references for appropriate attribution.
- [ ] Record last security-policy review date and owner.

## Cross-cutting engineering gates
- [ ] Create/modify the implementation only after the normative specification for this component is approved.
- [ ] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [ ] Add integration tests at every external boundary touched by this component.
- [ ] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [ ] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [ ] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [ ] Document operator/developer usage, known limits, and recovery behavior.
- [ ] Produce machine-readable evidence in the production acceptance bundle.
- [ ] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [ ] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [ ] Users can determine license terms, supported versions, ownership, and vulnerability-reporting process from the repository.
- [ ] Released packages contain required legal notices.
- [ ] CI detects missing or inconsistent governance metadata.

## Closure evidence to attach
- [ ] Specification/ADR/config/schema revision or file path.
- [ ] Implementation commit/source revision and changed modules.
- [ ] Unit + integration/contract test result references.
- [ ] Security/reliability/performance evidence applicable to this component.
- [ ] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [ ] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---
# Final production-readiness closure checklist

- [ ] MC-01 through MC-34 are each either **Closed** or covered by an approved, non-expired production waiver.
- [ ] All C001-C100 checklist requirements have fresh post-remediation evidence.
- [ ] `pk_core` and required sibling dependencies are repository-declared and reproducibly resolvable.
- [ ] No mandatory test is skipped in the release acceptance job.
- [ ] All schema/config/state compatibility checks pass.
- [ ] Threat-model high/critical risks have verified mitigations.
- [ ] Fault/disaster scenarios preserve hard safety and tenant/security invariants.
- [ ] Performance gates pass on the declared release reference environment.
- [ ] Soak/fleet-scale tests show no unbounded memory, queue, descriptor, task, telemetry-cardinality, or state growth.
- [ ] Health/readiness/explain surfaces report the exact active release/config/ownership state.
- [ ] CI generates a complete machine-readable production acceptance bundle.
- [ ] Release artifact, SBOM, checksums, provenance, evidence bundle, license, and security metadata are published together.
- [ ] Staged rollout/canary and rollback procedure has been exercised against the release candidate.
- [ ] Owner, security reviewer, release approver, and operations owner have signed off.
- [ ] A new independent post-remediation audit finds no undocumented production-critical component gaps.

---

**Checklist count:** 1468 actionable check boxes across global gates, 34 missing-component sections, and final production-readiness closure.

**Recommended status vocabulary:** `Not Started` · `In Design` · `Implementing` · `Verification` · `Evidence Pending` · `Blocked` · `Waived (expires YYYY-MM-DD)` · `Closed`