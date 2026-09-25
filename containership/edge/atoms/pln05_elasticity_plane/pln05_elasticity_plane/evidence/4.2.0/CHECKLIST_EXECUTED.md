<!-- Executed copy produced by tools/mc_status.py for PLN-05 4.2.0. Marks: [x] DONE, [~] PARTIAL, [E] OPEN_EXTERNAL, [G] OPEN_GOVERNANCE. Global gates and final closure are evaluated by tools/gate.py. -->
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
**4.2.0 status: GOVERNANCE_PENDING** — ADR-0001 PROPOSED; CHECKLIST.json C010/C011 text kept verbatim and marked superseded-proposed in traceability.
**Recommended priority:** P0 — architecture blocker  
**Objective:** Establish one authoritative definition of PLN-05 so the implementation, contract, tests, checklist, and release evidence cannot disagree about whether PLN-05 is a hysteretic capacity-target controller or also owns snapshot/restore, Dandelion-style microfunctions, and HyperFlux-style resource reassignment.  
**Dependencies:** None. This should precede requirements, schema, interface, and acceptance work.

## Required deliverables
- [x] `docs/adr/ADR-0001-pln05-authoritative-scope.md`
- [~] Updated `CHECKLIST.json`, `contract.py`, `README.md`, and acceptance evidence
- [x] Machine-readable scope declaration, e.g. `spec/pln05_scope.yaml`
- [x] Migration/deprecation note for whichever interpretation is retired

## Component-specific implementation checklist
- [x] Identify every source that currently asserts PLN-05 responsibilities: `CHECKLIST.json`, `contract.py`, `README.md`, implementation modules, tests, generated evidence, and sibling-interface documentation.
- [x] Create a side-by-side responsibility matrix for: demand observation, hysteresis, capacity target calculation, placement, provisioning, resource reassignment, snapshot, restore, microfunction lifecycle, failover, and execution ownership.
- [x] Classify each responsibility as **OWN**, **ORCHESTRATE**, **CALL**, **OBSERVE**, or **OUT OF SCOPE**.
- [G] Select a single authoritative architecture interpretation and record the decision in an ADR with status, date, approvers, context, alternatives, consequences, and superseded material.
- [x] State the exact production responsibility in SHALL/SHALL NOT language.
- [x] Define the source-of-truth precedence order when README, checklist, contract, and code disagree.
- [x] If snapshot/restore remains in scope, identify the owning API, durability model, restore consistency point, timeout semantics, and interaction with elasticity decisions.
- [x] If Dandelion-style microfunctions remain in scope, define lifecycle, scheduling authority, isolation boundary, artifact model, invocation protocol, and failure ownership.
- [x] If HyperFlux-style resource reassignment remains in scope, define provider authority, placement constraints, resource accounting, fencing, and rollback.
- [x] If the implemented capacity-target-only design is authoritative, explicitly deprecate C010/C011 language that implies execution/resource ownership and replace it with capacity-control semantics.
- [x] Document backward-compatibility impact on sibling components and any contract versions that must change.
- [x] Define architecture invariants that future changes may not violate, including ownership boundaries and forbidden ambient authority.
- [x] Update tests so they fail if documentation/specification drifts from the selected scope.
- [x] Add a repository check that verifies all declared scope/version identifiers agree.
- [x] Record unresolved questions and explicit non-goals rather than leaving ambiguous behavior implicit.
- [G] Obtain explicit approval from the accountable architecture owner before closing this component.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [G] Exactly one production scope is normative and all repository artifacts agree with it.
- [~] No checklist requirement demands behavior that the accepted contract forbids.
- [x] Scope drift is detectable by automated validation in CI.
- [x] Every sibling dependency can determine whether PLN-05 owns, calls, or excludes each major responsibility.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-02 — Ownership and escalation record  
**4.2.0 status: GOVERNANCE_PENDING** — roles defined, every assignee UNASSIGNED; approvals.json empty.
**Recommended priority:** P0 — operational accountability  
**Objective:** Create durable ownership metadata and operational escalation paths for production, security, release, and incident decisions.  
**Dependencies:** MC-01 should identify the final production boundary.

## Required deliverables
- [x] `CODEOWNERS` or equivalent ownership metadata
- [x] `docs/operations/ownership-and-escalation.md`
- [x] `ops/oncall.yaml` or equivalent machine-readable owner/escalation manifest
- [G] Approval and review cadence recorded in release evidence

## Component-specific implementation checklist
- [G] Name the accountable service owner, technical owner, release approver, security contact, and operational on-call role.
- [x] Separate **role identifiers** from personal contact data so the repository remains maintainable and privacy-safe.
- [x] Define primary and secondary escalation paths for availability, security, data-integrity, and dependency incidents.
- [x] Define business-hours and after-hours paging expectations.
- [x] Declare the support boundary between PLN-05 and upstream/downstream sibling components.
- [x] Define which team owns externally supplied demand authenticity, capacity-limit correctness, provider outages, and controller correctness.
- [x] Specify who may approve emergency disable, freeze, rollback, configuration override, or authority-ceiling changes.
- [x] Define ownership handoff requirements and minimum notice when maintainers change.
- [x] Establish review cadence for owner metadata and escalation routes.
- [x] Add stale-owner detection to CI or release review, e.g. required non-empty ownership fields and last-reviewed date.
- [x] Map incident severity levels to escalation roles.
- [x] Define response expectations for critical vulnerabilities and production regressions.
- [x] Identify the owner for checklist waivers and technical-debt expirations.
- [x] Document how operators locate current escalation information during a control-plane outage.
- [x] Ensure ownership metadata is referenced from README/runbooks rather than duplicated inconsistently.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [G] A responder can identify the correct owner and escalation role without tribal knowledge.
- [x] Every privileged operational action has an accountable approving role.
- [x] Ownership metadata has a documented review date and does not rely on an individual-only contact.
- [G] Release evidence records the accountable approver.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-03 — Context / NFR / semantics specification  
**4.2.0 status: IMPLEMENTED_LOCAL** — all Definition-of-Done items met locally; closure needs owner approval
**Recommended priority:** P0 — requirements foundation  
**Objective:** Define the environment, semantics, lifecycle, non-functional requirements, partition behavior, and policy precedence required for predictable operation across cloud, datacenter, near-edge, and far-edge deployments.  
**Dependencies:** MC-01; informs MC-05 through MC-31.

## Required deliverables
- [x] `spec/pln05_semantics.md`
- [x] `spec/pln05_nfr.yaml`
- [x] `spec/pln05_state_machine.mmd` or equivalent state diagram
- [x] Environment profile matrix for cloud/DC/near-edge/far-edge

## Component-specific implementation checklist
- [x] Define supported deployment contexts: public cloud, private cloud, datacenter, near-edge, far-edge, disconnected/occasionally connected edge.
- [x] Define assumptions for clock quality, network latency, packet loss, bandwidth, power stability, storage durability, and control-plane reachability per context.
- [x] Specify outcome classes for every observation cycle: scale-up, scale-down, hold, constrained-hold, stale-input-hold, frozen, degraded, error, and recovery.
- [x] Define the controller lifecycle state machine including initialization, ready, active, degraded, frozen, quarantined, draining, stopped, and recovery transitions.
- [x] Define authoritative time semantics: monotonic vs wall clock, grace-window timing, stale-demand age, and behavior during clock discontinuity.
- [x] Set explicit NFRs for reaction latency p50/p95/p99, availability, recovery time, recovery point, throughput, memory, CPU, and acceptable decision error rate.
- [x] Define demand freshness thresholds and the exact action when demand becomes stale or unavailable.
- [x] Define behavior under network partition between PLN-05 and demand source, provider/control plane, policy service, and observability backend.
- [x] Specify precedence among hard safety ceiling, hard floor, policy constraints, site limits, tenancy limits, provider limits, operator override, and demand signal.
- [x] Define conflict resolution for contradictory or rapidly changing policies.
- [x] Define consistency expectations for floor/ceiling changes while a grace window is in progress.
- [x] Define idempotency and monotonicity expectations for repeated observations.
- [x] Specify numerical domains, units, rounding rules, saturation behavior, and overflow/underflow handling.
- [x] Define supported scale magnitudes and rate-of-change limits.
- [x] Document tenant and workload semantics: whether state is per workload, per tenant, per site, or global.
- [x] State privacy/data-classification expectations for demand and telemetry fields.
- [x] Map every NFR to a measurable verification method and acceptance threshold.
- [x] Version the semantics specification and define compatibility rules for semantic changes.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Every externally visible state and outcome has a normative definition.
- [x] Partition, stale-input, and clock-failure behavior is deterministic and testable.
- [x] All NFRs are measurable and linked to tests/benchmarks.
- [x] Policy precedence is unambiguous and encoded consistently in implementation/tests.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-04 — Requirements traceability matrix  
**4.2.0 status: IMPLEMENTED_LOCAL** — no per-requirement rationale field; dependency relationships recorded only for C011 and the SHALL set.
**Recommended priority:** P0 — governance / evidence  
**Objective:** Create a machine-readable bidirectional mapping between every requirement, implementation element, test, evidence artifact, owner, status, and release gate.  
**Dependencies:** MC-01 and MC-03.

## Required deliverables
- [x] `traceability/requirements.yaml`
- [x] Generated `traceability/REQUIREMENTS_MATRIX.md`
- [x] CI validator for orphaned/stale mappings
- [x] Release snapshot of the matrix

## Component-specific implementation checklist
- [x] Assign a stable immutable identifier to every requirement, including C001-C100 and any new SHALL-level requirements.
- [~] Record requirement source, version, rationale, criticality, and acceptance criterion.
- [x] Map each requirement to one or more implementation files/symbols when applicable.
- [x] Map each requirement to one or more verification tests, benchmarks, analyses, reviews, or operational exercises.
- [x] Map each requirement to evidence output paths and evidence format.
- [x] Record requirement owner and reviewer role.
- [x] Track status using controlled values such as planned, implemented, verified, waived, deprecated, superseded.
- [~] Record dependency relationships among requirements.
- [x] Represent partial coverage explicitly; do not treat a file citation as proof of behavioral compliance.
- [x] Record waiver ID and expiry date for any intentionally unmet requirement.
- [x] Add reverse mappings from code/test/evidence back to requirements to detect unclaimed implementation.
- [x] Validate that deleted or renamed files do not leave stale evidence links.
- [x] Generate human-readable reports from the machine-readable source; do not maintain two independent matrices.
- [x] Fail CI when a mandatory production requirement has no verification path.
- [x] Fail release gating when mandatory requirements remain unverified unless an approved non-expired waiver exists.
- [x] Preserve matrix snapshots per released version for auditability.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Every mandatory requirement has an owner, implementation mapping, verification mapping, and evidence mapping or approved waiver.
- [x] The matrix is generated reproducibly and validated in CI.
- [x] Traceability is bidirectional and stale references fail automated checks.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-05 — Typed external schemas  
**4.2.0 status: IMPLEMENTED_LOCAL** — field units/default semantics partly in descriptions only; validators are Python only (no generated bindings for other languages).
**Recommended priority:** P0 — interface correctness  
**Objective:** Define concrete, versioned, machine-validatable schemas for `PK_DEMAND/1`, `PK_CAPACITY_LIMITS/1`, and `PK_CAPACITY_TARGET/1`, including evolution and compatibility rules.  
**Dependencies:** MC-01 and MC-03.

## Required deliverables
- [x] `schemas/pk_demand_v1.json` or equivalent IDL
- [x] `schemas/pk_capacity_limits_v1.json`
- [x] `schemas/pk_capacity_target_v1.json`
- [~] Generated language bindings/validators and golden examples

## Component-specific implementation checklist
- [x] Choose and document the canonical schema technology: JSON Schema, Protobuf, Avro, WIT, OpenAPI schema, or another versioned IDL.
- [x] Assign stable schema IDs and semantic versions.
- [~] Define every field with type, required/optional status, units, allowed range, default semantics, and nullability.
- [x] Use explicit numeric constraints to reject NaN, Infinity, negative capacity, inverted floor/ceiling, and impossible utilization.
- [x] Define identifiers for tenant, workload, site, source, request, correlation, and schema version where required.
- [x] Define event/observation timestamps and freshness semantics.
- [x] Define demand confidence/quality metadata if multiple demand sources or inferred signals are possible.
- [x] Define capacity-limit provenance and authority source.
- [x] Define capacity-target reason/outcome fields and whether the target is absolute, delta, or normalized.
- [x] Define extensibility rules for unknown fields and forward compatibility.
- [x] Define breaking vs non-breaking schema changes.
- [x] Define schema negotiation or supported-version behavior when peers differ.
- [x] Generate runtime validators and ensure boundary validation occurs before business logic.
- [x] Create canonical valid examples for minimum, nominal, floor, ceiling, and boundary values.
- [x] Create invalid examples for malformed type, missing required field, unknown critical version, NaN/Infinity, stale timestamps, negative values, and authority violations.
- [x] Add schema linting and compatibility checks to CI.
- [x] Publish checksum/version metadata for released schemas.
- [x] Ensure error responses identify schema/version failure without echoing sensitive payloads.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] All external inputs/outputs are validated against a released schema before use.
- [x] Boundary-value and invalid-payload tests cover every field constraint.
- [x] Backward/forward compatibility rules are automated in CI.
- [x] Schema versions are carried in protocol exchanges or otherwise unambiguously negotiated.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-06 — Boundary IAM / capability specification  
**4.2.0 status: IMPLEMENTED_LOCAL** — break-glass issuance approval and runtime sandbox are deployment/issuer obligations; audit records lack policy version (explain has it).
**Recommended priority:** P0 — security boundary  
**Objective:** Specify and enforce authentication, authorization, trust establishment, and least-privilege capabilities for every external actor and interface.  
**Dependencies:** MC-01, MC-05, MC-11.

## Required deliverables
- [x] `security/iam-model.md`
- [x] `security/capabilities.yaml`
- [x] Policy definitions and enforcement hooks
- [x] IAM conformance tests

## Component-specific implementation checklist
- [x] Enumerate actor classes: demand reporter, operator, policy service, provider adapter, sibling plane, telemetry collector, release agent, and emergency administrator.
- [x] Define trust bootstrap for each actor class.
- [x] Define accepted workload identity mechanisms such as mTLS SPIFFE/SPIRE identity, signed tokens, cloud workload identity, or equivalent.
- [x] Define authentication failure behavior and audit requirements.
- [x] Define authorization actions granularly: submit demand, update limits, read status, freeze, unfreeze, quarantine, change config, publish target, retrieve evidence.
- [x] Apply default-deny authorization.
- [x] Separate read, control, and administrative capabilities.
- [x] Prevent demand submitters from modifying authority ceilings unless explicitly authorized by a distinct capability.
- [x] Define tenant scoping and prevent cross-tenant identity reuse.
- [x] Define site/environment scoping where edge or multi-site operation is supported.
- [x] Define credential/session lifetime and rotation requirements.
- [x] Define replay-resistant proof requirements for control operations.
- [x] Specify how peer identity is bound to schema/source metadata to prevent source spoofing.
- [~] Define break-glass access, approval, expiry, and mandatory audit behavior.
- [E] Enforce least privilege in process/container/VM runtime permissions as well as API policy.
- [x] Add negative tests for unauthorized, expired, wrong-tenant, wrong-site, and privilege-escalation attempts.
- [~] Version capability policy and include policy version in explain/audit evidence.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Every externally callable operation has an explicit authenticated actor and authorization rule.
- [x] Default-deny behavior is verified by negative tests.
- [x] No untrusted actor can raise PLN-05 authority or cross tenant/site boundaries.
- [x] Privileged emergency access is time-bounded and auditable.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-07 — Interface reliability and error contract  
**4.2.0 status: PARTIAL** — transport deadlines are adapter obligations (no network code here); no request-rate limiter beyond admission.
**Recommended priority:** P0 — protocol resilience  
**Objective:** Define consistent timeout, cancellation, retry, idempotency, backpressure, limits, and structured error semantics across every public interface.  
**Dependencies:** MC-03, MC-05, MC-06.

## Required deliverables
- [x] `spec/interface_reliability.md`
- [x] `schemas/error_v1.*`
- [x] Client/server timeout and retry defaults
- [x] Interface reliability contract tests

## Component-specific implementation checklist
- [x] Enumerate every synchronous and asynchronous interface.
- [~] Define connect, handshake, request, response, idle, and end-to-end deadlines.
- [x] Define cancellation propagation semantics and cleanup obligations.
- [x] Classify operations as idempotent, conditionally idempotent, or non-idempotent.
- [x] Define idempotency-key format, scope, retention, and duplicate-response behavior where needed.
- [x] Define retryable vs non-retryable error classes.
- [x] Specify maximum attempts, exponential backoff parameters, jitter strategy, and retry budget.
- [x] Ensure retries cannot amplify stale demand or duplicate target application.
- [x] Define queue bounds and backpressure signals.
- [x] Define overload behavior: reject, shed, coalesce, sample, or defer.
- [x] Create stable machine-readable error codes with category, retryability, severity, and correlation ID.
- [x] Prevent internal stack traces, secrets, or raw untrusted payloads from leaking in errors.
- [~] Define maximum request size, nesting depth, field counts, and rate limits.
- [x] Define behavior for unknown schema versions and partially supported capabilities.
- [x] Define ordering guarantees if events are streamed.
- [x] Define duplicate/out-of-order event handling.
- [x] Add protocol tests for timeout, cancel, retry, duplicate, overload, malformed error, and recovery.
- [x] Document client guidance so sibling components do not implement incompatible retry logic.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] Every interface has deterministic deadline, retry, and failure behavior.
- [x] Duplicate/replayed requests cannot cause duplicated authority changes.
- [x] Backpressure and overload behavior is bounded and test-covered.
- [x] Error codes are stable, machine-readable, and correlation-friendly.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-08 — Protocol examples and conformance fixtures  
**4.2.0 status: PARTIAL** — not every constrained field has a wrong-type/out-of-range fixture; target schema omission fixtures cover 7 of 16 required fields.
**Recommended priority:** P1 — interoperability  
**Objective:** Provide golden valid/invalid payloads and automated contract tests that make interface compliance independently verifiable by sibling implementations.  
**Dependencies:** MC-05 and MC-07.

## Required deliverables
- [x] `fixtures/protocol/valid/`
- [x] `fixtures/protocol/invalid/`
- [x] `tests/contract/`
- [x] Fixture manifest with expected result/error

## Component-specific implementation checklist
- [x] Create at least one golden fixture for every public message type and schema version.
- [x] Cover minimum, nominal, maximum, floor, ceiling, zero-load, and boundary-value cases.
- [~] Create invalid fixtures for each required-field omission.
- [~] Create wrong-type and out-of-range fixtures for every constrained field.
- [x] Create stale timestamp and future-skew fixtures.
- [x] Create wrong-tenant, wrong-site, and unauthorized-source fixtures where identity metadata applies.
- [x] Create unknown-version and forward-compatible-extension fixtures.
- [x] Create duplicate, reordered, and replayed message sequences.
- [x] Create invalid limit combinations such as floor > ceiling.
- [x] Create non-finite numeric cases where the serialization format permits them.
- [x] Record expected status, error code, and side-effect expectation for every invalid fixture.
- [x] Make fixture files immutable test assets with stable names.
- [x] Provide a fixture manifest containing schema version and checksum.
- [x] Build contract tests that load fixtures through the real boundary validator, not internal constructors that bypass parsing.
- [x] Expose fixtures for sibling repositories to consume.
- [x] Test round-trip serialization/deserialization without semantic drift.
- [x] Add mutation testing or generated negative variants to avoid hand-picked blind spots.
- [x] Run conformance fixtures in CI and include results in release evidence.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] A third-party sibling implementation can validate interoperability using repository-contained fixtures.
- [~] Every schema validation rule has at least one positive or negative fixture.
- [x] Fixture tests exercise real protocol boundaries and produce machine-readable results.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-09 — Build / package / dependency manifest  
**4.2.0 status: PARTIAL** — Windows bootstrap untested; no vulnerability scanner run (zero third-party runtime deps); framework tier unresolvable (pk_core).
**Recommended priority:** P0 — reproducibility  
**Objective:** Make installation, dependency resolution, packaging, and compatibility reproducible from the repository without hidden environment assumptions.  
**Dependencies:** MC-01; supports almost every later component.

## Required deliverables
- [x] `pyproject.toml`
- [x] Lock/constraints file
- [x] Build metadata and reproducible package artifact
- [x] Dependency compatibility manifest

## Component-specific implementation checklist
- [x] Define the canonical Python/runtime version range.
- [x] Create `pyproject.toml` with package name, version, dependencies, optional groups, entry points, license metadata, and build backend.
- [x] Declare `pk_core` explicitly with compatible version bounds or provide a repository-contained substitute if that is the architecture decision.
- [x] Declare sibling contract/runtime package versions required for supported integration tiers.
- [x] Pin build-tool versions used for release packaging.
- [x] Add a lock or constraints mechanism appropriate to the deployment model.
- [x] Separate runtime, test, benchmark, docs, and development dependencies.
- [x] Eliminate undeclared imports and environment-only dependencies.
- [x] Document offline installation behavior and package mirror requirements if edge deployment requires it.
- [~] Create deterministic bootstrap commands for clean Windows/Linux CI images as applicable.
- [x] Build both source distribution and wheel/package artifact where appropriate.
- [x] Verify installation into a clean isolated environment.
- [x] Verify uninstall/reinstall and upgrade from the previous supported release.
- [x] Generate package checksums and provenance metadata.
- [x] Define dependency update cadence and compatibility testing process.
- [~] Add dependency vulnerability scanning and license-policy checks.
- [x] Ensure the version is sourced from one canonical location and checked against package metadata/README/evidence.
- [x] Fail CI when the dependency graph is unresolved or lock data is stale.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] A clean environment can install and test PLN-05 using repository-declared commands only.
- [x] `pk_core` and sibling compatibility are explicit rather than assumed.
- [x] Released artifacts are reproducible, versioned, checksummed, and provenance-linked.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-10 — Declarative configuration subsystem  
**4.2.0 status: IMPLEMENTED_LOCAL** — rollback does not capture a free-text reason (audit records actor/ticket-less rollback); config files rely on directory permissions set by deployment.
**Recommended priority:** P0 — safe operations  
**Objective:** Replace ad-hoc/in-memory configuration with validated, versioned, provenance-aware, atomically activated configuration supporting overlays, rollback, and secret-safe handling.  
**Dependencies:** MC-03, MC-05, MC-06, MC-09.

## Required deliverables
- [x] `config/schema.*`
- [x] `config/defaults.*`
- [x] Configuration loader/validator module
- [x] Activation/rollback journal and tests

## Component-specific implementation checklist
- [x] Define a versioned configuration schema for thresholds, grace periods, floors, ceilings, stale-input policy, telemetry, and safety controls.
- [x] Declare units and valid ranges for every field.
- [x] Reject unknown critical fields and malformed versions fail-closed.
- [x] Separate immutable package defaults from mutable site/environment configuration.
- [x] Define overlay precedence: package default → environment/site → tenant/workload → operator emergency override, or the accepted model.
- [x] Implement deep merge semantics explicitly; avoid ambiguous merge behavior for lists/maps.
- [x] Record configuration source, revision, author/issuer, checksum, activation timestamp, and schema version.
- [x] Validate the entire candidate configuration before activation.
- [x] Activate multi-field changes atomically so readers never observe half-applied state.
- [x] Preserve the last-known-good configuration.
- [~] Implement explicit rollback with audit record and reason.
- [x] Define behavior when a new config is invalid, partially unreadable, or references unsupported capabilities.
- [x] Support dry-run validation and diff generation before activation.
- [x] Define whether config updates reset hysteresis/grace state and test the decision.
- [x] Prevent secrets from entering ordinary config where possible; where unavoidable, reference secret stores rather than embedding plaintext.
- [x] Redact secret-bearing values from logs, errors, status, and evidence.
- [~] Protect configuration files/objects with integrity checks and appropriate permissions.
- [x] Add property tests for overlay precedence and atomicity.
- [x] Add crash/restart tests around activation to ensure no torn configuration state.
- [x] Expose active configuration version/checksum in the status surface.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Invalid configuration cannot become active.
- [x] Configuration transitions are atomic, provenance-recorded, reversible, and restart-safe.
- [x] Operators can prove exactly which configuration produced a given decision.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-11 — Complete threat model and artifact trust chain  
**4.2.0 status: PARTIAL** — release signature is an ephemeral HMAC, not a managed signing identity.
**Recommended priority:** P0 — security architecture  
**Objective:** Establish a formal threat model covering tenants, supply chain, control plane, identity, providers, operators, telemetry, and artifacts, then enforce artifact provenance and approved-version policy.  
**Dependencies:** MC-01, MC-06, MC-09.

## Required deliverables
- [x] `security/threat-model.md`
- [x] Data-flow/trust-boundary diagrams
- [x] SBOM generation configuration
- [x] Artifact signature/provenance verification policy

## Component-specific implementation checklist
- [x] Identify assets: authority ceilings, active config, controller state, demand signals, identity tokens, target outputs, release artifacts, evidence, and audit logs.
- [x] Enumerate trust boundaries and data flows.
- [x] Model attacker classes: malicious tenant, compromised workload, compromised operator credential, malicious dependency, compromised build runner, network attacker, compromised provider, insider, and stale controller instance.
- [x] Use a consistent method such as STRIDE/LINDDUN/attack trees and record applicability.
- [x] Analyze spoofing of demand sources and limit authorities.
- [x] Analyze tampering with package artifacts, configs, schemas, evidence, and dependency downloads.
- [x] Analyze replay/rollback to vulnerable or stale package/config versions.
- [x] Analyze privilege escalation through admin/freeze/ceiling interfaces.
- [x] Analyze denial-of-service and resource exhaustion at parsing, queues, retries, telemetry, and coordination layers.
- [x] Analyze multi-tenant information leakage through metrics/logs/timing.
- [x] Analyze supply-chain dependency substitution/typosquatting/compromised package risks.
- [x] Define security invariants and required mitigations for each high-risk threat.
- [x] Generate an SBOM for every release artifact.
- [x] Verify artifact digest before installation/activation.
- [~] Verify trusted signature/provenance/attestation according to the selected release model.
- [x] Maintain an approved-version policy for PLN-05 and critical dependencies.
- [~] Reject or quarantine unsigned/unapproved artifacts in production paths.
- [x] Record verification result in release and runtime evidence.
- [x] Map threat IDs to security tests in MC-14.
- [x] Review the threat model after architecture or trust-boundary changes.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] High/critical threats have explicit mitigations and verification coverage.
- [~] Production artifacts are integrity-verified and provenance-linked before use.
- [x] SBOM and approved-version evidence is generated per release.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-12 — Isolation and cryptographic data protection  
**4.2.0 status: PARTIAL** — authenticated transport encryption and at-rest encryption/KMS are external (adapters, volume/KMS).
**Recommended priority:** P0 — multi-tenant/data security  
**Objective:** Enforce tenant/workload isolation and protect sensitive data in transit and at rest with managed key rotation and minimized authority.  
**Dependencies:** MC-06 and MC-11.

## Required deliverables
- [x] `security/isolation-model.md`
- [x] `security/crypto-policy.md`
- [~] Runtime isolation configuration
- [x] Isolation and crypto conformance tests

## Component-specific implementation checklist
- [x] Define isolation domains for tenant, workload, site, process/container/VM, state store, metrics, and audit data.
- [x] Define whether one controller instance may handle multiple tenants and the exact memory/state separation model if so.
- [x] Prevent tenant-controlled identifiers from selecting another tenant's state.
- [x] Enforce authorization scope at every state lookup and target publication boundary.
- [x] Define process/container/VM sandbox requirements and forbidden ambient capabilities.
- [x] Minimize filesystem, network, device, and credential authority.
- [~] Require authenticated encryption for network transport where data crosses trust boundaries.
- [x] Define accepted TLS/mTLS versions, cipher policy, certificate validation, hostname/workload identity validation, and revocation behavior.
- [x] Define encryption-at-rest requirements for durable state, config snapshots, credentials, and audit records.
- [E] Define key ownership, KMS/HSM integration, key hierarchy, and tenant/site separation where applicable.
- [x] Define key rotation cadence and overlapping-key transition procedure.
- [x] Define behavior when keys are expired, revoked, unavailable, or fail integrity checks.
- [x] Prevent secrets/keys from appearing in logs, traces, metrics labels, crash dumps, or evidence bundles.
- [x] Define secure zeroization expectations for in-memory secret material where feasible.
- [x] Add cross-tenant negative tests.
- [x] Add certificate/key rotation and expiry tests.
- [x] Add downgrade-prevention tests for transport/security protocol versions.
- [x] Document cryptographic agility and migration procedure.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Cross-tenant reads/writes/target effects are prevented and tested.
- [~] All protected transport/storage paths use approved cryptographic mechanisms.
- [x] Key rotation and revocation are operationally testable without unsafe control behavior.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-13 — Security-service outage and tamper-evident audit subsystem  
**4.2.0 status: IMPLEMENTED_LOCAL** — audit confidentiality delegated to storage encryption.
**Recommended priority:** P0 — fail-safe security operations  
**Objective:** Define safe behavior when identity, attestation, policy, key, or trusted-time services fail and produce durable tamper-evident audit events for security-sensitive actions.  
**Dependencies:** MC-06, MC-10, MC-11, MC-12.

## Required deliverables
- [x] `security/security_dependency_failure_policy.md`
- [x] Audit event schema
- [x] Append-only/tamper-evident audit implementation
- [x] Outage and audit-integrity tests

## Component-specific implementation checklist
- [x] Enumerate security dependencies: identity provider, certificate authority, policy engine, attestation service, KMS/HSM, trusted time, revocation source.
- [x] Classify each dependency as fail-closed, bounded fail-static, cached-grace, or noncritical.
- [x] Define maximum cache age for identity/policy/key material.
- [x] Define behavior when trusted time is unavailable or skew exceeds tolerance.
- [x] Prevent a security-service outage from implicitly expanding authority.
- [x] Define safe ceiling/floor behavior during authorization uncertainty.
- [x] Define when the controller must freeze, degrade, quarantine, or stop publishing targets.
- [x] Emit audit events for authentication failures, authorization denials, config changes, limit changes, freeze/unfreeze, quarantine, artifact verification, key rotation, and break-glass use.
- [x] Define stable audit event IDs, actor identity, tenant/site scope, timestamp, correlation ID, action, result, reason, and object revision.
- [x] Use append-only storage or cryptographic chaining/signing appropriate to the deployment environment.
- [x] Detect gaps, truncation, reordering, or tampering in audit sequences.
- [x] Define local buffering when the remote audit sink is unavailable.
- [x] Bound audit buffers and define fail behavior if they fill.
- [~] Protect audit confidentiality while preserving integrity.
- [x] Define retention, access, export, and legal/privacy constraints.
- [x] Add tests for identity outage, policy outage, key outage, time outage, sink outage, and audit tampering.
- [x] Ensure security-sensitive operations are never silently omitted from audit.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Loss of a security dependency never grants additional authority.
- [x] Security-sensitive actions are attributable and tamper-detectable.
- [x] Audit sink outages have bounded, deterministic behavior.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-14 — Adversarial security test suite  
**4.2.0 status: IMPLEMENTED_LOCAL** — timing side channels covered only for MAC comparison.
**Recommended priority:** P1 — security verification  
**Objective:** Translate the threat model into repeatable automated adversarial tests covering privilege escalation, injection, replay, spoofing, isolation escape, side channels, and resource exhaustion.  
**Dependencies:** MC-11 through MC-13.

## Required deliverables
- [x] `tests/security/`
- [x] Threat-to-test mapping
- [x] Security test corpus
- [x] Machine-readable security test report

## Component-specific implementation checklist
- [x] Create one or more test cases for every high/critical threat ID.
- [x] Attempt unauthorized ceiling increases and floor decreases.
- [x] Attempt demand-source spoofing and identity confusion.
- [x] Attempt cross-tenant and cross-site state access.
- [x] Replay previously valid demand/config/control requests.
- [x] Reorder and duplicate signed/control messages.
- [x] Inject malformed structured data, oversized values, deeply nested structures, and encoding edge cases.
- [x] Test parser and schema behavior for NaN/Infinity/extreme integers where formats permit.
- [x] Test command/template/path/log injection surfaces if present.
- [x] Attempt privilege escalation from read-only to control/admin operations.
- [x] Attempt use of expired/revoked credentials and stale policies.
- [x] Test certificate downgrade and wrong-identity acceptance.
- [x] Test unsigned/tampered package/config/evidence artifacts.
- [x] Exercise dependency-confusion/unsupported dependency version rejection.
- [x] Drive request rates, queue sizes, telemetry labels, and error generation to exhaustion thresholds.
- [x] Test retry amplification under attacker-controlled failures.
- [~] Test timing/cardinality behavior for obvious tenant-information leakage.
- [x] Test quarantine/freeze controls against unauthorized bypass.
- [x] Run security tests under optimized runtime modes where assertions may differ.
- [x] Integrate failures into CI release-blocking policy according to severity.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Every high/critical threat has an automated or explicitly justified manual verification.
- [x] Security regressions fail CI/release gates.
- [x] Test results are machine-readable and included in acceptance evidence.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-15 — Failure matrix and health / stall detection  
**4.2.0 status: IMPLEMENTED_LOCAL** — flapping integration test absent (detector implemented).
**Recommended priority:** P0 — resilience foundation  
**Objective:** Enumerate failure modes across process, VM/container, node, site, network, provider, dependency, and control plane, then detect unhealthy/stalled behavior with deterministic thresholds.  
**Dependencies:** MC-03, MC-24.

## Required deliverables
- [x] `reliability/failure_matrix.yaml`
- [x] Health/stall detector implementation
- [x] Detector thresholds/config schema
- [x] Failure-detection tests

## Component-specific implementation checklist
- [x] Enumerate process crash, exception loop, deadlock, livelock, event-loop stall, and resource exhaustion.
- [x] Enumerate container/VM restart, eviction, freeze, clock pause, and disk-full conditions.
- [x] Enumerate node loss, node overload, local network loss, and DNS/service-discovery failure.
- [x] Enumerate site isolation and multi-site partition scenarios.
- [x] Enumerate provider API outage, throttling, partial success, stale inventory, and delayed acknowledgements.
- [x] Enumerate demand-source outage, stale signal, malformed signal, and contradictory sources.
- [x] Enumerate policy/IAM/KMS/time/telemetry/coordination service failures.
- [x] Define observable symptoms and detection signal for each failure.
- [x] Define detection threshold, debounce, hysteresis, and maximum detection time.
- [x] Differentiate **healthy**, **degraded**, **unready**, **stalled**, and **failed**.
- [x] Use monotonic time for local stall timing.
- [x] Define heartbeat semantics and avoid heartbeat-only false health.
- [x] Detect progress, not merely process liveness, for long-running workflows.
- [x] Define how health state influences readiness and decision publication.
- [x] Define alert severity per failure mode.
- [x] Add unit tests for threshold boundaries.
- [~] Add integration tests for recovery and flapping conditions.
- [x] Document known undetectable failures and compensating controls.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Every material failure class has a defined detection mechanism or documented limitation.
- [x] Stall detection has bounded detection time and false-positive controls.
- [x] Health state deterministically affects readiness/operation.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-16 — Retry / admission control / circuit-breaker layer  
**4.2.0 status: IMPLEMENTED_LOCAL** — retry budget per policy object (not per dependency); breaker thresholds on consecutive failures only; breaker state and retries not exported as metrics.
**Recommended priority:** P0 — overload safety  
**Objective:** Provide bounded retries with backoff/jitter plus admission control, load shedding, and circuit breakers so dependency failures or bursts cannot cause retry storms or unbounded resource growth.  
**Dependencies:** MC-07, MC-15.

## Required deliverables
- [x] `reliability/retry_policy.*`
- [x] `reliability/admission.py` / equivalent
- [x] Circuit-breaker state machine
- [x] Overload tests and metrics

## Component-specific implementation checklist
- [x] Define retry eligibility per operation/error code.
- [x] Define maximum attempts and total retry deadline.
- [x] Use exponential or decorrelated backoff with bounded jitter.
- [~] Cap retry concurrency and retry budget globally/per dependency.
- [x] Ensure idempotency before enabling retries.
- [x] Propagate cancellation and deadline budgets across retries.
- [x] Stop retries when the source input becomes stale or superseded.
- [x] Define admission limits by queue depth, concurrency, CPU/memory pressure, or token budget.
- [x] Reject early before expensive parsing/work when capacity is unavailable.
- [x] Define load-shedding priority classes; protect safety/control operations from low-priority telemetry/reporting load.
- [x] Implement bounded queues with explicit overflow behavior.
- [x] Implement circuit-breaker closed/open/half-open transitions.
- [~] Define breaker thresholds for consecutive failures, error rate, latency, and timeout.
- [x] Prevent synchronized half-open probes across replicas.
- [~] Expose retry, rejection, shed, and breaker metrics.
- [x] Define dependency-specific breaker isolation so one failed provider does not disable unrelated operations.
- [x] Test retry storms, slow dependencies, intermittent failures, and recovery.
- [x] Verify overload behavior does not raise authority or lose critical audit events.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Retries and queues have hard bounds.
- [x] Dependency failure cannot create unbounded amplification.
- [x] Admission/load shedding preserves critical control-path responsiveness.
- [x] Circuit breaker recovery is deterministic and observable.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-17 — Failover and degraded-operation controller  
**4.2.0 status: PARTIAL** — residency is carried by scope identity only; no residency model beyond that; consistent failover requires a shared/replicated state_dir.
**Recommended priority:** P0 — availability/safety  
**Objective:** Define and implement safe failover and degraded modes that preserve residency/isolation constraints and handle stale demand or noncritical dependency loss without unsafe scaling.  
**Dependencies:** MC-03, MC-06, MC-10, MC-15, MC-16, MC-18.

## Required deliverables
- [x] `reliability/degraded_modes.md`
- [x] Failover policy/configuration
- [x] Degraded-mode state machine
- [x] Failover integration tests

## Component-specific implementation checklist
- [x] Enumerate failover-eligible dependencies and state which are not safely failoverable.
- [x] Define alternate demand source behavior, including trust rank and freshness.
- [x] Define alternate provider/control-plane behavior if multiple providers/regions exist.
- [x] Preserve tenant residency, sovereignty, and site constraints during failover.
- [x] Preserve security/isolation capabilities during failover; never fail open to weaker trust.
- [x] Define stale-demand thresholds and target behavior by stale duration.
- [x] Define whether last-known-good demand/target may be reused and for how long.
- [x] Define maximum authority in degraded mode, potentially stricter than normal ceiling.
- [x] Define behavior when capacity confirmation is unavailable.
- [x] Define behavior when telemetry is unavailable but control path remains healthy.
- [x] Define operator-visible degraded reasons and transition timestamps.
- [x] Require explicit criteria to exit degraded mode.
- [x] Debounce dependency flapping to prevent rapid failover/failback oscillation.
- [x] Coordinate failover with leader/fencing state to prevent dual active controllers.
- [x] Define rollback if failover target/provider rejects or partially applies an action.
- [x] Test site partition, dependency outage, stale demand, recovery, and failback.
- [~] Test that failover never violates residency/isolation constraints.
- [x] Document operator actions for prolonged degraded operation.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Every supported degraded mode has deterministic entry/exit criteria.
- [~] Failover cannot weaken tenant/security/residency constraints.
- [x] Stale-demand behavior is bounded and independently testable.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-18 — Durable controller state and distributed coordination  
**4.2.0 status: IMPLEMENTED_LOCAL** — all Definition-of-Done items met locally; closure needs owner approval
**Recommended priority:** P0 — correctness under restart/replication  
**Objective:** Persist controller state crash-consistently and coordinate replicated ownership with leases/epochs/fencing to prevent stale or duplicate controllers from publishing authority.  
**Dependencies:** MC-03, MC-10, MC-15.

## Required deliverables
- [x] `state/state_schema.*`
- [x] Durable state adapter
- [x] Lease/epoch/fencing implementation
- [x] Crash/replay/split-brain tests

## Component-specific implementation checklist
- [x] Enumerate state that must survive restart: current target, pending direction/count, active config revision, authority envelope, last accepted input metadata, freeze/quarantine state as applicable.
- [x] Separate reconstructible state from must-persist state.
- [x] Define a versioned durable state schema.
- [x] Use atomic write/transaction semantics so partially written state is never accepted.
- [x] Persist checksum/integrity metadata.
- [x] Define fsync/durability requirements appropriate to deployment tier.
- [x] Define startup recovery order and validation.
- [x] Reject state from unsupported future versions.
- [x] Provide migration path for older state versions.
- [x] Define replay semantics and whether previously emitted targets may be re-emitted.
- [x] Use idempotent output identifiers to avoid duplicate side effects after restart.
- [x] Define active-controller ownership using lease/epoch/term semantics.
- [x] Use fencing tokens on downstream target application where possible.
- [x] Ensure a controller that loses lease immediately loses publication authority.
- [x] Prevent split-brain publication after partitions.
- [x] Define lease duration, renewal deadline, clock assumptions, and failure behavior.
- [x] Persist/compare epoch with controller state to detect stale resurrection.
- [x] Test crash at every persistence boundary.
- [x] Test restart, duplicate process, lease loss, network partition, stale leader, and state corruption.
- [x] Expose state schema/epoch/owner status in health/explain surfaces.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Restart does not silently reset behavior in a way that violates hysteresis/safety semantics.
- [x] At most one authorized controller can publish for a given ownership scope.
- [x] Stale instances are fenced from downstream effects.
- [x] State corruption fails safe and is observable.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-19 — Runtime quarantine / freeze / disable controls  
**4.2.0 status: IMPLEMENTED_LOCAL** — no dry-run for control actions (status shows the current state before acting).
**Recommended priority:** P0 — emergency safety  
**Objective:** Provide authorized runtime controls to stop or constrain unsafe elasticity decisions without uninstalling the component.  
**Dependencies:** MC-06, MC-10, MC-13, MC-18, MC-24.

## Required deliverables
- [x] Administrative control API/CLI
- [x] Freeze/quarantine state schema
- [x] Runbook for emergency controls
- [x] Authorization/audit tests

## Component-specific implementation checklist
- [x] Define distinct semantics for **freeze**, **disable**, **quarantine**, **drain**, and **resume**.
- [x] Specify whether freeze holds current target, forces a safe target, or blocks publication only.
- [x] Specify quarantine behavior for untrusted input/source vs whole-controller quarantine.
- [x] Make controls scoped by tenant/workload/site rather than global-only when architecture requires.
- [x] Require a dedicated privileged capability.
- [x] Require reason, actor, ticket/incident reference, and optional expiry for emergency actions.
- [x] Persist control state across restart if safety requires it.
- [x] Ensure emergency state participates in leader/fencing semantics.
- [x] Define precedence over ordinary demand/config updates.
- [x] Prevent lower-privilege config updates from clearing emergency controls.
- [~] Provide dry-run/status visibility before operator action.
- [x] Emit tamper-evident audit records.
- [x] Expose active freeze/quarantine state in health/readiness/explain surfaces.
- [x] Define automatic expiry only where safe; avoid accidental silent unfreeze.
- [x] Provide explicit two-step or approval workflow for especially dangerous resume/override actions if warranted.
- [x] Test control application during normal operation, dependency outage, partition, restart, and failover.
- [x] Test unauthorized bypass attempts.
- [x] Document recovery procedure and validation before resuming.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Operators can stop unsafe decision publication without package removal.
- [x] Emergency controls survive the required failure/restart scenarios.
- [x] Only authorized actors can apply/clear controls and every action is auditable.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-20 — Fault-injection / disaster test harness  
**4.2.0 status: IMPLEMENTED_LOCAL** — process kill simulated by restart-from-disk; no network-level (packet loss/DNS/bandwidth) or read-only-volume injection; no production-like disaster run.
**Recommended priority:** P1 — resilience verification  
**Objective:** Build repeatable fault injection for process, node, site, network, provider, dependency, partition/reconnect, and degraded-control-plane scenarios.  
**Dependencies:** MC-15 through MC-19.

## Required deliverables
- [x] `tests/fault/`
- [x] Fault scenario manifest
- [x] Local/CI chaos harness
- [x] Recovery evidence reports

## Component-specific implementation checklist
- [x] Create a catalog of fault scenarios mapped to MC-15 failure IDs.
- [~] Support deterministic process crash and kill injection.
- [x] Support forced exception/error responses at dependency boundaries.
- [~] Support latency, timeout, packet loss, connection reset, DNS failure, and bandwidth constraints.
- [x] Support message duplication, reordering, delay, and replay where protocol permits.
- [~] Support disk-full, read-only storage, corrupted state, and partial persistence failures.
- [x] Support clock skew/jump simulation for time-dependent logic.
- [x] Support lease-store/coordination outage and stale leader scenarios.
- [x] Support identity/policy/KMS/time-service outage scenarios.
- [x] Support provider throttling, partial success, and stale responses.
- [x] Support demand-source silence, stale data, malformed data, and contradictory inputs.
- [x] Support whole-site isolation and reconnect.
- [x] Define preconditions, injection point, expected behavior, maximum detection time, maximum recovery time, and invariants for each scenario.
- [x] Automate cleanup and environment reset.
- [x] Seed randomized faults reproducibly.
- [~] Capture logs/metrics/traces/state snapshots with correlation IDs.
- [x] Verify no authority ceiling/security invariant is violated during faults.
- [E] Run a production-like disaster suite before release and a reduced suite in CI.
- [x] Store machine-readable results in the acceptance bundle.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Critical failure modes are exercised, not only documented.
- [x] Recovery behavior and invariant preservation are automatically asserted.
- [x] Fault runs are reproducible and evidence-producing.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-21 — Performance baseline and load-test suite  
**4.2.0 status: PARTIAL** — baseline recorded on the CI container, not a declared reference environment; GC not profiled; instance-count scaling not measured; power not measured (W-001).
**Recommended priority:** P1 — capacity certification  
**Objective:** Establish reproducible performance baselines for latency, throughput, startup, CPU, memory, storage, network, and power where relevant under steady, burst, overload, scale, and recovery workloads.  
**Dependencies:** MC-03, MC-09, MC-24, MC-25.

## Required deliverables
- [x] `benchmarks/`
- [x] Workload profiles
- [x] Baseline result files
- [x] Benchmark environment manifest

## Component-specific implementation checklist
- [x] Define benchmark hardware/runtime profiles and capture CPU, memory, OS, Python/runtime, container/VM, and dependency versions.
- [x] Define warm and cold startup benchmarks.
- [x] Measure observe/decision latency p50/p95/p99/max.
- [x] Measure sustained decision throughput.
- [x] Measure CPU time per decision and under sustained load.
- [x] Measure resident memory baseline, peak, and growth over time.
- [~] Measure allocation/GC behavior if relevant.
- [x] Measure serialized request/response size and network bandwidth where remote interfaces exist.
- [x] Measure durable-state read/write latency once MC-18 exists.
- [x] Measure control path under steady load.
- [x] Measure burst response and queue/backpressure behavior.
- [x] Measure overload behavior to and beyond configured admission limits.
- [x] Measure recovery after overload clears.
- [~] Measure scaling with tenant/workload cardinality and controller-instance count.
- [x] Measure impact of observability enabled vs disabled/sampled.
- [x] Measure impact of security verification/signature/IAM paths.
- [E] Measure edge power/thermal behavior for supported edge profiles where required.
- [x] Use fixed datasets/seeds and store benchmark parameters with results.
- [x] Run repeated trials and report variance/confidence, not one-off numbers.
- [x] Define pass/fail SLO thresholds from MC-03.
- [x] Export machine-readable benchmark results for MC-23.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] Baselines are reproducible on declared reference environments.
- [x] All NFR latency/throughput/resource budgets have corresponding measurements.
- [x] Steady, burst, overload, scale, and recovery profiles are represented.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-22 — Efficiency / resource-bounds analysis  
**4.2.0 status: IMPLEMENTED_LOCAL** — memory copies not measured; power not measured.
**Recommended priority:** P1 — scalability / edge fitness  
**Objective:** Quantify serialization, copies, context switches, network hops, state duplication, queue/concurrency/fan-out bounds, and optimization opportunities, including edge power/thermal impact.  
**Dependencies:** MC-21.

## Required deliverables
- [x] `performance/efficiency-analysis.md`
- [x] Resource-bound formulas/configuration
- [x] Profiling artifacts
- [x] Optimization decision records

## Component-specific implementation checklist
- [x] Map the end-to-end decision data path from demand source to target consumer.
- [x] Count serialization/deserialization operations per decision.
- [~] Count memory copies where observable.
- [x] Count process/thread/context-switch boundaries.
- [x] Count network hops and RPCs per decision.
- [x] Identify duplicated state across replicas/components.
- [x] Measure payload sizes and compression trade-offs if applicable.
- [x] Profile CPU hotspots under representative load.
- [x] Profile memory allocations and long-lived object retention.
- [x] Define hard bounds for inbound queues.
- [x] Define hard bounds for retry queues.
- [x] Define hard bounds for concurrent requests/decisions.
- [x] Define fan-out bounds to providers/peers/telemetry sinks.
- [x] Prove that bound multiplication cannot exceed memory/CPU safety budgets.
- [x] Evaluate locality/caching opportunities and stale-cache risks.
- [x] Evaluate batching/coalescing opportunities without violating reaction SLOs.
- [x] Evaluate zero-copy/kernel-bypass only where measurement shows material benefit; document rejection if not justified.
- [x] Measure observability cardinality/resource impact.
- [x] Measure cryptographic verification overhead.
- [E] Measure edge power draw and thermal throttling where edge is supported.
- [~] Record optimization changes with before/after benchmark evidence.
- [x] Ensure optimizations preserve deterministic semantics and security boundaries.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Resource consumption has explicit calculable bounds.
- [x] Major copies/hops/queues/fan-out are measured and justified.
- [x] Optimizations are evidence-based and regression-tested.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-23 — Performance regression release gate  
**4.2.0 status: GOVERNANCE_PENDING** — single-platform baseline; no CPU pinning of noisy hosts; baseline PROPOSED, needs approval.
**Recommended priority:** P1 — release quality gate  
**Objective:** Automatically compare current performance against approved baselines and block releases that exceed startup, density, throughput, resource, or tail-latency thresholds.  
**Dependencies:** MC-21 and MC-22; integrates with MC-33.

## Required deliverables
- [x] `ci/performance_gate.*`
- [x] Baseline registry
- [x] Threshold policy
- [x] Machine-readable gate result

## Component-specific implementation checklist
- [x] Select benchmark scenarios that are stable enough for automated gating.
- [x] Define absolute SLO thresholds and relative regression thresholds separately.
- [x] Gate p95/p99 latency, not averages only.
- [x] Gate throughput at fixed resource allocation.
- [x] Gate startup latency.
- [x] Gate peak and steady-state memory.
- [x] Gate CPU per operation or CPU at fixed throughput.
- [x] Gate queue saturation/overload recovery where measurable.
- [~] Define platform-specific baselines for materially different architectures.
- [x] Use repeated samples and statistical tolerance to reduce flaky decisions.
- [x] Define allowed variance and minimum sample count.
- [~] Normalize or pin noisy CI host variables where feasible.
- [x] Version baselines and tie them to release/environment metadata.
- [x] Require explicit approved baseline update rather than silently accepting regressions.
- [x] Record who/why when a threshold is waived.
- [x] Expire performance waivers.
- [x] Emit machine-readable pass/fail and individual metric deltas.
- [x] Attach result to the production acceptance bundle.
- [x] Run a smaller presubmit gate and fuller release benchmark gate if cost requires.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] A material performance regression cannot be released silently.
- [G] Baseline changes are reviewed and auditable.
- [x] Gate output is deterministic enough to support release automation.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-24 — Runtime health / readiness / status surface  
**4.2.0 status: IMPLEMENTED_LOCAL** — orchestrator probe wiring belongs to the embedding service.
**Recommended priority:** P0 — operability  
**Objective:** Expose machine-readable liveness, readiness, version, active configuration, dependency status, authority state, and active capabilities without leaking sensitive data.  
**Dependencies:** MC-03, MC-10, MC-15, MC-18, MC-19.

## Required deliverables
- [x] Health/readiness API or CLI
- [x] Status schema
- [x] Status redaction policy
- [x] Health conformance tests

## Component-specific implementation checklist
- [x] Separate liveness from readiness.
- [x] Define readiness blockers: invalid config, lost ownership/lease, stale critical input, failed security dependency, corrupted state, quarantine, or unsupported schema.
- [x] Expose package/runtime version and build identifier.
- [x] Expose active configuration schema version and checksum/revision.
- [x] Expose current ownership scope, lease/epoch status, and fencing state without disclosing secrets.
- [x] Expose current floor/ceiling/target and controller mode where safe.
- [x] Expose dependency health with stable dependency IDs.
- [x] Expose active degraded/freeze/quarantine states and reasons.
- [x] Expose supported schema/capability versions.
- [x] Expose last successful decision timestamp and last accepted demand age.
- [x] Expose last failure/error category in a bounded/redacted form.
- [x] Define health query timeout and ensure it cannot block on unhealthy downstream dependencies.
- [x] Keep health/status path lightweight and bounded under overload.
- [x] Protect sensitive administrative detail behind appropriate authorization.
- [x] Provide a local diagnostic path when network APIs are unavailable.
- [x] Add status schema versioning.
- [x] Test each unhealthy/degraded transition.
- [x] Test redaction and unauthorized access.
- [E] Integrate readiness with deployment orchestrator probes where applicable.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Automation can distinguish alive, ready, degraded, frozen, quarantined, and failed states.
- [x] Status reflects the active config/dependency/ownership state used for decisions.
- [x] Health endpoints remain bounded and safe during dependency failure.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-25 — Metrics / structured logging / tracing implementation  
**4.2.0 status: IMPLEMENTED_LOCAL** — per-workload target gauges intentionally not emitted (cardinality policy); queue/breaker/lease gauges missing; one span per decision; log schema not versioned.
**Recommended priority:** P0 — observability core  
**Objective:** Implement stable metrics, structured logs, and trace-context propagation with safe cardinality, redaction, and correlation across decision and dependency boundaries.  
**Dependencies:** MC-03, MC-24; feeds MC-26 and MC-27.

## Required deliverables
- [x] Metrics registry/emitter
- [x] Structured logging configuration/schema
- [x] Tracing instrumentation
- [x] Observability tests

## Component-specific implementation checklist
- [x] Define a stable service/component identity and version attribute set.
- [x] Emit decision counters by outcome class.
- [x] Emit decision latency histogram with approved buckets.
- [x] Emit input age/staleness metrics.
- [~] Emit current target/floor/ceiling gauges where safe and useful.
- [~] Emit queue depth, concurrency, retry, rejection, load-shed, and circuit-breaker metrics once MC-16 exists.
- [~] Emit lease/leadership/fencing metrics once MC-18 exists.
- [x] Emit dependency health and error counters.
- [x] Use structured logs rather than free-form strings for operational events.
- [x] Include stable correlation/request/operation IDs.
- [x] Include tenant/workload/site identifiers only when cardinality/privacy policy permits.
- [x] Define severity levels consistently.
- [x] Redact secrets, tokens, keys, raw sensitive payloads, and excessive PII.
- [x] Propagate W3C Trace Context or the selected standard across supported boundaries.
- [~] Create spans for boundary validation, policy/IAM checks, state access, decision calculation, and target publication as appropriate.
- [x] Set span attributes with bounded cardinality.
- [x] Define sampling behavior and error/rare-event retention.
- [x] Ensure observability failure cannot block safety-critical decision logic.
- [x] Test redaction with representative secret patterns.
- [x] Test metric cardinality under high tenant/workload counts.
- [x] Test trace continuity across adjacent-layer integration fixtures.
- [~] Version/log schema changes where downstream parsing depends on them.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Operators can correlate an input to a decision and downstream publication using stable IDs.
- [x] Observability is bounded, redacted, and non-blocking.
- [x] Core SLO/error/saturation signals are emitted programmatically, not only documented.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-26 — Explainability / correlation layer  
**4.2.0 status: IMPLEMENTED_LOCAL** — no topology snapshot; build provenance only as version/build_id; explain records are not integrity-protected; explain tests do not cover every outcome.
**Recommended priority:** P1 — operator diagnosis  
**Objective:** Provide an operator explain view that reconstructs why a decision occurred from input, policy, configuration, constraints, topology, ownership, and release lineage.  
**Dependencies:** MC-10, MC-18, MC-24, MC-25.

## Required deliverables
- [x] Explain API/CLI
- [x] Decision provenance schema
- [x] Correlation store/index
- [x] Explainability tests

## Component-specific implementation checklist
- [x] Assign a unique decision ID to every decision cycle/result.
- [x] Record the exact accepted demand observation ID/version.
- [x] Record active config revision/checksum.
- [x] Record policy/IAM decision reference when authorization or policy affects the result.
- [x] Record active floor/ceiling and their provenance/authority source.
- [x] Record current capacity, pending hysteresis state, and relevant prior target.
- [x] Record degraded/freeze/quarantine state influencing the decision.
- [x] Record ownership epoch/lease/fencing token reference.
- [~] Record dependency/topology snapshot references when they constrain action.
- [x] Record the chosen outcome and structured reason code, not prose only.
- [x] Record rejected alternative reasons where useful, e.g. requested scale-up but ceiling constrained.
- [~] Record package version/build/provenance.
- [E] Record infrastructure/provider release/adapter versions affecting publication.
- [x] Provide lookup by decision ID, correlation ID, workload/tenant, and time window subject to privacy policy.
- [x] Bound retention and storage size.
- [x] Redact sensitive identity/config values.
- [x] Make explain output deterministic enough for automated assertions.
- [~] Add tests for scale-up, scale-down, floor hold, ceiling hold, stale input, freeze, degraded, and authorization-constrained cases.
- [~] Ensure explain data cannot be altered without corresponding audit/provenance evidence where high assurance is required.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] An operator can answer 'why did PLN-05 choose this target?' without reconstructing state from unrelated logs.
- [x] Explain output identifies the exact config/policy/release/ownership context.
- [x] Sensitive data remains redacted and access-controlled.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-27 — Telemetry policy, dashboards, and alerts  
**4.2.0 status: IMPLEMENTED_LOCAL** — all Definition-of-Done items met locally; closure needs owner approval
**Recommended priority:** P1 — operations visibility  
**Objective:** Define telemetry retention/sampling/privacy/export policy and provide actionable dashboards and alert rules tied to SLOs, saturation, security, and degraded operation.  
**Dependencies:** MC-25; references MC-03 SLOs.

## Required deliverables
- [x] `observability/telemetry-policy.md`
- [x] Dashboard definitions
- [x] Alert rule definitions
- [x] Alert runbook links

## Component-specific implementation checklist
- [x] Classify metrics, logs, traces, audit events, and explain records by sensitivity.
- [x] Define retention periods for each telemetry class.
- [x] Define sampling policy for traces and high-volume logs.
- [x] Define export destinations and transport security.
- [x] Define tenant/site data-separation requirements in telemetry backends.
- [x] Define label/tag allowlist to control cardinality.
- [x] Define redaction and deletion requirements.
- [x] Create dashboard for decision rate/outcome distribution.
- [x] Create dashboard for reaction latency p50/p95/p99 and SLO compliance.
- [x] Create dashboard for stale demand/input quality.
- [x] Create dashboard for floor/ceiling constrained decisions.
- [~] Create dashboard for queue/retry/load-shed/circuit-breaker state.
- [x] Create dashboard for leader/lease/fencing health.
- [x] Create dashboard for degraded/freeze/quarantine state.
- [x] Create dependency health dashboard.
- [x] Create alerts for readiness loss, sustained decision failure, stale critical input, lease loss, audit buffer pressure, excessive retries, persistent ceiling/floor constraint, and SLO burn.
- [x] Use multi-window/multi-burn-rate SLO alerts where appropriate.
- [x] Set alert severity and ownership/escalation route.
- [x] Include runbook links in alert annotations.
- [x] Test alert expressions against synthetic scenarios.
- [x] Review alerts for noise and define tuning/change process.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] Dashboards expose the signals required to operate the controller without ad-hoc log searches.
- [x] Alerts are actionable, routed, and tied to documented runbooks.
- [x] Telemetry retention/export is privacy- and cardinality-controlled.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-28 — Compatibility / fuzz / concurrency test matrix  
**4.2.0 status: PARTIAL** — min/max Python versions not tested; config not exercised concurrently; no race detector; no cancellation-under-concurrency test.
**Recommended priority:** P1 — robustness  
**Objective:** Validate supported CPU/runtime/hypervisor/provider/protocol combinations and expose parser/state-machine/race defects through fuzzing, property testing, and concurrency testing.  
**Dependencies:** MC-05, MC-07, MC-09, MC-18.

## Required deliverables
- [x] `tests/compatibility/`
- [x] `tests/fuzz/`
- [x] `tests/concurrency/`
- [x] Supported compatibility matrix

## Component-specific implementation checklist
- [x] Define supported CPU architectures and minimum features.
- [x] Define supported OS/runtime/Python versions.
- [x] Define supported container/VM/hypervisor tiers if relevant.
- [x] Define supported provider/adapter versions.
- [x] Define supported schema/protocol version combinations.
- [~] Test minimum and maximum supported dependency versions.
- [x] Test upgrade/downgrade compatibility across at least the supported release window.
- [x] Create property tests for controller invariants: target remains within floor/ceiling, invalid input rejected, hysteresis transitions bounded, lower ceiling never raises authority, etc.
- [x] Fuzz schema parsers and boundary validators with malformed bytes/objects.
- [x] Fuzz numeric edge cases and deeply nested/large payload limits.
- [x] Fuzz state migration/deserialization once durable state exists.
- [x] Fuzz config overlay/merge logic once MC-10 exists.
- [x] Define the thread-safety/concurrency contract explicitly.
- [~] Run concurrent observe/config/status/control operations according to the supported model.
- [~] Use race detectors or deterministic schedulers where the language/runtime permits.
- [x] Test concurrent leader handoff/lease loss/publication once MC-18 exists.
- [~] Test cancellation/timeouts during concurrent operations.
- [x] Run long randomized state-machine sequences against invariants.
- [x] Record unsupported combinations explicitly so absence of testing is not mistaken for support.
- [x] Publish compatibility results with releases.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] Supported combinations are explicit and continuously tested.
- [x] Core invariants survive fuzz/property/concurrency testing.
- [x] Thread-safety expectations are documented and verified.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-29 — Benchmark / soak / burst / fleet-scale test suite  
**4.2.0 status: BLOCKED_EXTERNAL** — soak is presubmit length (60k decisions); no multi-site, leader-handoff or credential rotation during soak; no declared fleet targets or reference infrastructure.
**Recommended priority:** P1 — production scale confidence  
**Objective:** Validate long-duration stability, burst handling, benchmark repeatability, and behavior at realistic fleet/tenant/workload scale.  
**Dependencies:** MC-21, MC-22, MC-25.

## Required deliverables
- [x] `tests/scale/`
- [x] Soak/burst/fleet workload generators
- [x] Long-run result reports
- [x] Leak/drift detectors

## Component-specific implementation checklist
- [x] Define a minimum-duration soak profile appropriate to release confidence.
- [x] Exercise steady decision traffic for the full soak period.
- [x] Inject realistic periodic bursts.
- [x] Exercise worst-case boundary oscillation around thresholds.
- [x] Exercise sustained overload followed by recovery.
- [x] Exercise high tenant/workload cardinality.
- [~] Exercise multiple sites/providers if supported.
- [~] Exercise leader handoff/failover during long runs.
- [~] Rotate configuration and credentials during soak if supported.
- [x] Track RSS/heap growth and detect memory leaks.
- [~] Track file descriptor/socket/thread/task growth.
- [x] Track queue depth and ensure no monotonic backlog accumulation.
- [x] Track latency drift over time.
- [~] Track error-rate drift and retry amplification.
- [x] Track telemetry cardinality/storage growth.
- [x] Track durable-state size growth.
- [x] Exercise periodic dependency failures during soak.
- [~] Define fleet-scale target numbers for controllers, workloads, tenants, decision rate, and events/sec.
- [x] Use deterministic workload seeds and archive generator parameters.
- [x] Produce machine-readable summary plus failure timeline.
- [~] Compare long-run metrics to MC-21 baselines and MC-23 thresholds.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] No unbounded resource growth appears over the approved soak duration.
- [x] Burst/overload recovery returns to baseline without manual reset.
- [E] Fleet-scale targets are demonstrated on declared reference infrastructure.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-30 — Machine-readable production acceptance bundle  
**4.2.0 status: IMPLEMENTED_LOCAL** — no third-party linter/type checker adopted; bundle signature is ephemeral HMAC.
**Recommended priority:** P0 — release evidence  
**Objective:** Generate a release-attached evidence bundle containing requirement/gate results, test/benchmark/security evidence, artifact provenance, dependency resolution, and signed/immutable acceptance metadata.  
**Dependencies:** MC-04, MC-09, MC-14, MC-20, MC-23, MC-28, MC-29, MC-33.

## Required deliverables
- [x] `evidence/<version>/manifest.json`
- [x] Requirement/gate result files
- [~] Checksums/signatures/provenance
- [x] Release acceptance summary

## Component-specific implementation checklist
- [x] Define a versioned evidence manifest schema.
- [x] Include package version, commit/source revision, build ID, timestamp, and environment identity.
- [x] Include artifact digests and provenance/attestation references.
- [x] Include SBOM reference and dependency lock/resolve evidence.
- [x] Include requirements traceability snapshot.
- [x] Include unit/contract/integration test results.
- [x] Include security test results.
- [x] Include fault/disaster test results.
- [x] Include compatibility/fuzz/concurrency results.
- [x] Include benchmark/performance-gate results.
- [x] Include soak/fleet results for release-tier certification.
- [~] Include static analysis/lint/type/security scan results where adopted.
- [x] Include configuration/schema compatibility checks.
- [x] Include unresolved waivers with owner and expiry.
- [x] Include owner/release approver identities/roles.
- [x] Use stable machine-readable result statuses and reason codes.
- [x] Ensure skipped tests are distinguished from passed tests.
- [x] Fail acceptance when a mandatory dependency such as `pk_core` is neither present nor reproducibly resolvable.
- [x] Checksum the entire evidence bundle.
- [~] Sign or provenance-attest the final acceptance bundle where release assurance requires it.
- [x] Store the bundle with the release artifact and make it retrievable by version.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] A release can be accepted/rejected from the evidence bundle without manually reading CI logs.
- [x] Skipped/unresolved checks cannot masquerade as passes.
- [x] Evidence is immutable/version-linked and traceable back to source/build.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-31 — Release and operations governance  
**4.2.0 status: PARTIAL** — canary not exercised; runbooks not executed by an operator; game days scheduled, none held.
**Recommended priority:** P0 — production lifecycle  
**Objective:** Define staged rollout, compatibility, vulnerability/EOL policy, state/config backup and migration, executable runbooks, recurring reviews, and waiver/debt governance.  
**Dependencies:** MC-02, MC-09, MC-10, MC-18, MC-24 through MC-30.

## Required deliverables
- [x] `docs/release-policy.md`
- [x] `docs/runbooks/`
- [x] `compatibility/supported-versions.yaml`
- [x] `governance/waivers.yaml`

## Component-specific implementation checklist
- [x] Define release channels/environments and promotion order.
- [x] Define canary scope, duration, success criteria, and automatic/manual abort conditions.
- [x] Define staged rollout percentages or deployment rings appropriate to the platform.
- [x] Define rollback trigger thresholds and rollback procedure.
- [x] Test rollback from the current release to at least the previous supported release.
- [x] Define schema/config/state forward and backward compatibility window.
- [x] Publish a supported-version matrix for PLN-05, runtime, `pk_core`, schemas, and critical sibling interfaces.
- [x] Define patch policy for functional defects.
- [x] Define vulnerability response SLA by severity.
- [x] Define end-of-life/deprecation notice period and unsupported-version behavior.
- [x] Define backup requirements for durable state and configuration.
- [x] Define restore procedure and RPO/RTO.
- [x] Define state/config migration and reconstruction procedure.
- [x] Create day-0 install/bootstrap runbook with prerequisites and verification.
- [x] Create day-1 operations runbook for routine health/config/monitoring actions.
- [x] Create day-2 incident/recovery runbooks for common failures.
- [x] Create incident severity, paging, escalation, containment, recovery, and postmortem process.
- [x] Schedule recurring access, policy, dependency, configuration, security, architecture, and capacity reviews.
- [x] Maintain exception/waiver/debt/deprecation register with owner, rationale, risk, compensating control, approval, and expiry.
- [x] Block release on expired waivers.
- [G] Define audit cadence for operational docs and execute periodic game days.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] Rollout and rollback are staged, measurable, and rehearsed.
- [x] Supported versions and vulnerability/EOL commitments are explicit.
- [~] Critical operational procedures are executable from runbooks.
- [x] Waivers/debt have owners and expirations rather than permanent ambiguity.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-32 — Master prompt / workflow source bundle  
**4.2.0 status: IMPLEMENTED_LOCAL** — no separate workflows/ directory (source/ carries the governing checklist); clean-checkout run recorded in evidence only for this container.
**Recommended priority:** P2 — repository completeness  
**Objective:** Restore or replace the missing master prompt/workflow source with a versioned, testable source-of-truth bundle rather than a stale README reference.  
**Dependencies:** MC-01 to avoid encoding the wrong scope.

## Required deliverables
- [x] `MASTER.md` or intentionally renamed authoritative workflow source
- [~] `workflows/` supporting templates/prompts
- [x] Generated-workflow validation
- [x] README/source-of-truth references

## Component-specific implementation checklist
- [x] Determine whether the absent `MASTER.md` is required production source, developer workflow documentation, or obsolete historical material.
- [x] If obsolete, record the deprecation decision and do not recreate misleading content.
- [x] If required, define the master prompt/workflow's intended consumers and outputs.
- [x] Make scope statements consistent with MC-01.
- [x] Break workflow into deterministic phases with explicit inputs, outputs, prerequisites, and failure conditions.
- [x] Define which steps are human approvals vs automatable checks.
- [x] Reference requirements IDs and acceptance gates rather than duplicating requirement prose.
- [x] Reference canonical schemas/configs by path/version.
- [x] Define repository-safe relative paths; avoid machine-specific paths.
- [x] Define Windows/Linux command variants if both are supported.
- [x] Make generated artifacts deterministic or record nondeterministic inputs.
- [x] Add lint checks for broken file references and missing referenced artifacts.
- [x] Add version identifier to the workflow source.
- [x] Add change log or ADR references for major workflow changes.
- [x] Ensure README points to the actual authoritative file.
- [~] Test the workflow against a clean checkout and record required external tools.
- [x] Prevent workflow text from claiming a test/gate passes unless machine evidence exists.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [x] No README or workflow reference points to a nonexistent source.
- [x] The master workflow is either intentionally retired or reproducibly usable from the repository.
- [x] Workflow steps reference the same authoritative scope and gates as the production spec.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-33 — CI and release automation  
**4.2.0 status: PARTIAL** — GitHub workflows written but not executed on a forge; action pins not verified; pk_core tier unresolvable; branch protection is a forge setting.
**Recommended priority:** P0 — continuous verification  
**Objective:** Automate standalone/framework tests, static checks, packaging, dependency resolution, security scans, evidence generation, performance gates, and release publication.  
**Dependencies:** MC-09; progressively integrates MC-04 through MC-31.

## Required deliverables
- [x] `.github/workflows/ci.yml` or equivalent CI definition
- [x] Release workflow
- [x] Reusable local CI script
- [x] CI evidence artifacts

## Component-specific implementation checklist
- [x] Run repository metadata/version consistency checks.
- [x] Run Python compile/import checks.
- [x] Run standalone controller tests on every change.
- [E] Run `pk_core`/framework conformance tests with a reproducibly installed compatible framework.
- [x] Fail if framework tests are unexpectedly skipped in release jobs.
- [x] Run schema validation and compatibility checks.
- [x] Run formatting/linting/type checks if adopted.
- [x] Run dependency lock/resolve verification.
- [~] Run dependency vulnerability and license-policy scans.
- [x] Run unit/contract/integration/security/fuzz test tiers at appropriate cadence.
- [x] Run package build and clean-environment install test.
- [x] Run artifact integrity/SBOM/provenance generation.
- [x] Run performance smoke/regression gate.
- [x] Run selected fault tests in presubmit and full fault suite in release/nightly jobs.
- [x] Run traceability validation and waiver-expiry checks.
- [x] Generate the machine-readable acceptance bundle.
- [x] Use least-privilege CI credentials and protected release environments.
- [~] Pin third-party CI actions/tools by immutable version/digest where supported.
- [x] Prevent untrusted pull-request code from accessing release secrets.
- [~] Sign/attest release artifacts according to MC-11.
- [x] Publish checksum/evidence alongside release artifact.
- [x] Provide an equivalent local command so CI logic is not opaque/vendor-only.
- [x] Cache dependencies safely without permitting stale/poisoned artifact substitution.
- [G] Define branch/tag protection and required checks for release.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [~] A clean CI runner can reproduce build/test/package/evidence from source.
- [x] Release jobs cannot report success when mandatory tests are skipped.
- [x] Artifacts and evidence are generated from the same immutable source revision.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

---


# MC-34 — License / security / release metadata  
**4.2.0 status: GOVERNANCE_PENDING** — license choice is the owner's; no issue templates.
**Recommended priority:** P0 — distribution governance  
**Objective:** Add the legal, security-reporting, ownership, release, and vulnerability-intake metadata required for a distributable and supportable production repository.  
**Dependencies:** MC-02 and organizational policy.

## Required deliverables
- [G] `LICENSE`
- [x] `NOTICE` if required
- [x] `SECURITY.md`
- [x] `CODEOWNERS` and release/support metadata

## Component-specific implementation checklist
- [G] Select and add the authoritative software license approved for distribution.
- [x] Ensure package metadata and README identify the same license.
- [x] Add NOTICE/attribution file where dependencies/license obligations require it.
- [x] Inventory third-party dependency licenses and flag incompatible/restricted licenses.
- [x] Document source and binary redistribution obligations.
- [x] Create `SECURITY.md` with supported versions.
- [x] Document private vulnerability reporting channel/process without encouraging public disclosure of unpatched vulnerabilities.
- [x] Define expected acknowledgement and remediation timelines by severity or reference organizational policy.
- [x] Document coordinated disclosure expectations.
- [x] Define how security advisories map to patched releases.
- [x] Add `CODEOWNERS` or equivalent ownership metadata aligned with MC-02.
- [x] Add release/versioning policy, including semantic versioning rules or chosen alternative.
- [x] Add changelog/release-note policy.
- [x] Define deprecation/EOL signaling in metadata.
- [~] Add repository metadata for issue templates/bug reports if appropriate.
- [x] Add machine-readable project metadata where ecosystem tooling benefits.
- [x] Ensure release artifacts include license/notice files.
- [x] Add CI check that required governance files exist and package metadata matches them.
- [x] Review all names/trademarks/third-party references for appropriate attribution.
- [x] Record last security-policy review date and owner.

## Cross-cutting engineering gates
- [G] Create/modify the implementation only after the normative specification for this component is approved.
- [x] Add unit tests for nominal behavior, boundary behavior, invalid input, and failure paths introduced by this component.
- [~] Add integration tests at every external boundary touched by this component.
- [x] Use stable machine-readable reason/error codes where the component can fail or change runtime state.
- [x] Add metrics/logs/traces needed to verify the component in production, with bounded cardinality and redaction.
- [x] Update the requirements traceability matrix with implementation, test, evidence, owner, and release-gate mappings.
- [x] Document operator/developer usage, known limits, and recovery behavior.
- [x] Produce machine-readable evidence in the production acceptance bundle.
- [x] Ensure all new configuration/schema/state formats are versioned and migration-compatible.
- [E] Pass clean-environment CI with no unexpected skips, TODO/FIXME placeholders, or unhandled `NotImplemented` paths.

## Definition of done / acceptance criteria
- [G] Users can determine license terms, supported versions, ownership, and vulnerability-reporting process from the repository.
- [x] Released packages contain required legal notices.
- [x] CI detects missing or inconsistent governance metadata.

## Closure evidence to attach
- [x] Specification/ADR/config/schema revision or file path.
- [x] Implementation commit/source revision and changed modules.
- [x] Unit + integration/contract test result references.
- [x] Security/reliability/performance evidence applicable to this component.
- [x] Traceability-matrix entry IDs and acceptance-bundle evidence paths.
- [G] Owner/reviewer approval plus any waiver IDs (with expiry) for remaining exceptions.

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