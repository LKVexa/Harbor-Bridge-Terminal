# GAP-10 v4.2.0 Missing Components — Professional Engineering Checklist

**Source:** `GAP10_v4.2.0_MISSING_COMPONENTS.md` from the audited/hardened GAP-10 v4.2.0 package  
**Purpose:** Convert the 40 audited missing production capabilities into implementation, verification, security, resilience, operations, and release gates.  
**Status convention:** Every checkbox is intentionally open. Completion means evidence exists and has been reviewed; code presence alone is not sufficient.  

## Global acceptance rules

- [ ] No dependency loss, restart, stale sample, trust failure, policy failure, state corruption, or controller failover may accidentally produce a less restrictive ceiling.
- [ ] Every externally visible interface SHALL be versioned, typed, bounded, authenticated where trust is required, and covered by contract tests.
- [ ] Every capacity-increasing change SHALL be attributable to a validated policy/configuration revision, trusted input, and authorized actor or controller.
- [ ] Every safety-critical state transition SHALL be explainable from retained evidence and correlated across metrics, logs, traces, audit records, and downstream enforcement.
- [ ] Production certification SHALL use machine-readable evidence tied to one exact source revision, build digest, policy set, schema set, compatibility matrix, and test report.
- [ ] P0 items SHALL be closed before production enforcement. P1 items SHALL be closed before normal production operation. P2/P3 items may proceed in parallel only after the P0 enforcement/state path is stable.
- [ ] Exceptions SHALL be explicit, owned, risk-assessed, time-bounded, and must not silently redefine a failed requirement as passed.

## Required evidence fields for every completed checklist item

- [ ] Implementation/change reference (commit/PR/build)
- [ ] Requirement ID(s)
- [ ] Test or validation evidence
- [ ] Reviewer/approver
- [ ] Date
- [ ] Operational/runbook impact
- [ ] Security impact classification
- [ ] Rollback/recovery reference
- [ ] Known residual risk/exception ID, if any

## 01. Authenticated telemetry adapter for GAP-09 [P0]

**Traceability:** `C021-C024, C041-C048`  
**Audited gap:** a concrete adapter that accepts only attested temperature/power/battery samples and carries source identity, freshness, and signature status into GAP-10.  
**Primary checklist profile:** `adapter`

### A. Component-specific engineering requirements

- [ ] Accept telemetry only when the producing GAP-09 identity is authenticated and authorized for the declared node/sensor scope.
- [ ] Carry sensor identity, node identity, measurement timestamp, receive timestamp, attestation result, signature result, and source sequence/revision into the canonical sample.
- [ ] Verify signed/attested telemetry before parsing values into trusted scheduling fields; treat verification failure as unusable evidence.
- [ ] Validate temperature in degrees Celsius, power in watts, battery fraction/percent, and optional sensor health fields against explicit schemas and physical plausibility limits.
- [ ] Enforce maximum telemetry age and future-clock-skew using the GAP-10 freshness policy; never “refresh” stale source timestamps on receipt.
- [ ] Detect replay/out-of-order samples using source sequence numbers and/or monotonic observed timestamps per sensor stream.
- [ ] Aggregate multi-sensor input without dropping the trust status of the most restrictive contributing sample.
- [ ] Define behavior for partially trusted nodes where some sensors are valid and others are missing or rejected.
- [ ] Expose counters for accepted, stale, future, malformed, unauthenticated, unauthorized, bad-signature, and replayed samples.
- [ ] Create GAP-09 interoperability fixtures covering key rotation, schema version mismatch, clock skew, node re-enrollment, and duplicate delivery.

### B. Architecture, security, resilience, and operability

- [ ] Define the adapter boundary as a separately testable module with no implicit ambient authority or hidden transport assumptions.
- [ ] Version every inbound and outbound message contract and reject unsupported major schema versions deterministically.
- [ ] Normalize peer-specific payloads into canonical GAP-10 domain objects before any scheduling decision is evaluated.
- [ ] Preserve source identity, correlation IDs, evidence timestamps, trust state, and policy revision across translation.
- [ ] Make duplicate delivery idempotent and prove that retries cannot multiply side effects or relax a ceiling.
- [ ] Bound connection pools, outstanding RPCs, payload sizes, decode time, queue depth, and per-peer concurrency.
- [ ] Specify explicit timeout, cancellation, retry, and backpressure behavior for every remote operation.
- [ ] Fail closed on malformed, unauthenticated, stale, ambiguous, or unsupported peer data.
- [ ] Expose peer compatibility, negotiated version, last-success time, and current degraded mode through health telemetry.
- [ ] Provide contract fixtures for nominal, boundary, malformed, stale, replayed, downgraded, and emergency cases.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Authenticated telemetry adapter for GAP-09.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] versioned adapter schema/contracts.
- [ ] positive and negative interoperability fixtures.
- [ ] integration test report with peer versions and applied outcomes.
- [ ] adapter health/metrics specification.
- [ ] security/authentication test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 02. Downstream scheduler enforcement adapter [P0]

**Traceability:** `C021, C030, C054`  
**Audited gap:** integration that makes `PK_POWER_CEILING/1` a hard admission/placement ceiling rather than advisory data.  
**Primary checklist profile:** `adapter`

### A. Component-specific engineering requirements

- [ ] Map `PK_POWER_CEILING/1` node decisions into the scheduler admission and placement primitive that actually limits allocatable capacity.
- [ ] Ensure an excluded/emergency node cannot accept new placement regardless of ordinary scheduler score or workload priority.
- [ ] Treat missing/unhealthy GAP-10 data as constrained according to the fail-closed contract, never as 100% capacity.
- [ ] Bind each admission decision to the GAP-10 ceiling revision/decision ID that was consulted.
- [ ] Prevent time-of-check/time-of-use races by revalidating the ceiling immediately before commit or using a transactional/fenced scheduler API.
- [ ] Handle capacity decreases below already allocated load with explicit eviction, preemption, drain, or no-new-admission semantics.
- [ ] Define how fractional ceilings are converted into scheduler-specific CPU/GPU/memory/power tokens without rounding upward unsafely.
- [ ] Confirm downstream rejection/acceptance and surface enforcement lag as a health failure when the applied ceiling differs from the desired ceiling.
- [ ] Test competing placement requests during a simultaneous nominal→critical transition.
- [ ] Prove via integration test that no scheduler code path, fallback queue, or manual placement path bypasses the ceiling.

### B. Architecture, security, resilience, and operability

- [ ] Define the adapter boundary as a separately testable module with no implicit ambient authority or hidden transport assumptions.
- [ ] Version every inbound and outbound message contract and reject unsupported major schema versions deterministically.
- [ ] Normalize peer-specific payloads into canonical GAP-10 domain objects before any scheduling decision is evaluated.
- [ ] Preserve source identity, correlation IDs, evidence timestamps, trust state, and policy revision across translation.
- [ ] Make duplicate delivery idempotent and prove that retries cannot multiply side effects or relax a ceiling.
- [ ] Bound connection pools, outstanding RPCs, payload sizes, decode time, queue depth, and per-peer concurrency.
- [ ] Specify explicit timeout, cancellation, retry, and backpressure behavior for every remote operation.
- [ ] Fail closed on malformed, unauthenticated, stale, ambiguous, or unsupported peer data.
- [ ] Expose peer compatibility, negotiated version, last-success time, and current degraded mode through health telemetry.
- [ ] Provide contract fixtures for nominal, boundary, malformed, stale, replayed, downgraded, and emergency cases.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Downstream scheduler enforcement adapter.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] versioned adapter schema/contracts.
- [ ] positive and negative interoperability fixtures.
- [ ] integration test report with peer versions and applied outcomes.
- [ ] adapter health/metrics specification.
- [ ] security/authentication test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 03. Elasticity-plane enforcement adapter [P0]

**Traceability:** `C021, C030`  
**Audited gap:** propagation of reduced ceilings to scale-out/scale-in logic so autoscaling cannot immediately refill thermally constrained capacity.  
**Primary checklist profile:** `adapter`

### A. Component-specific engineering requirements

- [ ] Propagate GAP-10 ceiling reductions into autoscaler effective capacity so scale-out demand does not refill a thermally constrained node/site.
- [ ] Define whether scaling decisions consume node-level, pool-level, rack-level, or site-level aggregate power/thermal headroom.
- [ ] Prevent positive feedback loops where reduced capacity causes scale-out onto nodes within the same constrained cooling/power domain.
- [ ] Apply hysteresis/debounce to elasticity reactions separately from the safety ceiling so rapid scaling does not oscillate.
- [ ] Define scale-in priority for constrained nodes while respecting disruption budgets and workload durability constraints.
- [ ] Preserve emergency exclusion as absolute even when minimum-replica or availability targets would otherwise request more placement.
- [ ] Expose desired versus applied elasticity limit and the GAP-10 decision revision that caused it.
- [ ] Test simultaneous autoscaler demand spikes and thermal derating across multiple nodes in one site.
- [ ] Test recovery so capacity is restored only after GAP-10 hysteresis and downstream convergence are both satisfied.
- [ ] Verify no elasticity fallback mode substitutes stale unconstrained capacity during GAP-10/control-plane loss.

### B. Architecture, security, resilience, and operability

- [ ] Define the adapter boundary as a separately testable module with no implicit ambient authority or hidden transport assumptions.
- [ ] Version every inbound and outbound message contract and reject unsupported major schema versions deterministically.
- [ ] Normalize peer-specific payloads into canonical GAP-10 domain objects before any scheduling decision is evaluated.
- [ ] Preserve source identity, correlation IDs, evidence timestamps, trust state, and policy revision across translation.
- [ ] Make duplicate delivery idempotent and prove that retries cannot multiply side effects or relax a ceiling.
- [ ] Bound connection pools, outstanding RPCs, payload sizes, decode time, queue depth, and per-peer concurrency.
- [ ] Specify explicit timeout, cancellation, retry, and backpressure behavior for every remote operation.
- [ ] Fail closed on malformed, unauthenticated, stale, ambiguous, or unsupported peer data.
- [ ] Expose peer compatibility, negotiated version, last-success time, and current degraded mode through health telemetry.
- [ ] Provide contract fixtures for nominal, boundary, malformed, stale, replayed, downgraded, and emergency cases.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Elasticity-plane enforcement adapter.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] versioned adapter schema/contracts.
- [ ] positive and negative interoperability fixtures.
- [ ] integration test report with peer versions and applied outcomes.
- [ ] adapter health/metrics specification.
- [ ] security/authentication test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 04. Durable per-node state store [P0]

**Traceability:** `C032, C057, C058, C095`  
**Audited gap:** persistence/reconstruction of band, last trusted sample, policy version, and hysteresis state across process restart/failover.  
**Primary checklist profile:** `state`

### A. Component-specific engineering requirements

- [ ] Persist per-node band, last accepted trusted sample metadata, last accepted sample timestamp/sequence, policy revision, ceiling, exclusion state, and hysteresis state.
- [ ] Define a stable node key that resists accidental state inheritance when hardware is reprovisioned or node names are reused.
- [ ] Store enough provenance to decide whether recovered state is compatible with the currently active policy revision.
- [ ] On empty/corrupt/incompatible state, reconstruct to the conservative startup state rather than nominal.
- [ ] Use atomic writes or a transactional store so band and associated sample/policy metadata cannot diverge.
- [ ] Protect against rollback to older store snapshots that would reaccept replayed telemetry or reopen capacity.
- [ ] Define state compaction without deleting evidence needed for replay/freshness/ownership safety.
- [ ] Implement schema migrations with forward-only safety checks and rollback procedures.
- [ ] Test crash at every persistence boundary and verify post-restart state is equal or more restrictive than pre-crash state.
- [ ] Provide operator tooling to inspect/reconstruct one node without editing raw state directly.

### B. Architecture, security, resilience, and operability

- [ ] Define the authoritative state model, key space, ownership, revision field, and serialization format.
- [ ] Specify crash-consistency semantics for every write and the exact state visible after partial process failure.
- [ ] Use compare-and-swap, fencing token, transactional write, or equivalent concurrency control where multiple writers are possible.
- [ ] Persist enough information to reconstruct the most restrictive safe state after restart without trusting missing evidence.
- [ ] Define TTL/expiry semantics separately for telemetry-derived state, policy state, and ownership leases.
- [ ] Document migration rules for backward/forward-compatible state schema evolution.
- [ ] Encrypt sensitive state at rest when it contains security, tenant, site, or infrastructure identifiers.
- [ ] Provide integrity protection or authenticated storage semantics for safety-critical records.
- [ ] Define snapshot, compaction, backup, restore, and corruption-recovery procedures.
- [ ] Prove through restart and failover tests that recovery never yields a less restrictive ceiling than justified by durable evidence.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Durable per-node state store.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] state schema and migration specification.
- [ ] crash-consistency/restart test report.
- [ ] backup/restore or reconstruction drill evidence.
- [ ] ownership/transaction semantics document.
- [ ] state integrity and retention policy.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 05. Atomic policy distribution and activation service [P0]

**Traceability:** `C033-C038`  
**Audited gap:** site/environment policy delivery with validation, staged activation, provenance, rollback, and immutable revision IDs.  
**Primary checklist profile:** `policy`

### A. Component-specific engineering requirements

- [ ] Define policy scopes for global, environment, site, hardware class, cooling domain, battery class, and node override with deterministic merge precedence.
- [ ] Validate thermal threshold ordering, recovery margins, battery reserve ranges, power ratio bands, maximum sample age, future skew, and zero emergency ceiling.
- [ ] Perform dry-run validation against representative telemetry before promotion to an enforcement stage.
- [ ] Use immutable revision IDs and content digests; never mutate an already-activated revision in place.
- [ ] Activate one complete revision atomically across all policy fields required for a decision.
- [ ] Define staged rollout cohorts and abort conditions for policy-only changes independently of code rollout.
- [ ] Keep an immediately available last-known-good signed revision for rollback.
- [ ] Reject policy activation if referenced hardware calibration, key set, or schema version is unavailable.
- [ ] Expose active/pending/previous revision and activation health through the readiness/explain interface.
- [ ] Generate machine-readable activation evidence including validator output, approver, signature, rollout cohort, and result.

### B. Architecture, security, resilience, and operability

- [ ] Represent policy as a versioned immutable document with a unique revision ID and content digest.
- [ ] Define an explicit schema covering thresholds, hysteresis, ceilings, reserve rules, scope selectors, and emergency behavior.
- [ ] Validate ordering invariants, units, numeric ranges, mandatory zero-capacity emergency semantics, and cross-field constraints before activation.
- [ ] Separate policy authoring, approval, distribution, activation, and rollback roles.
- [ ] Make activation atomic per declared scope and prevent mixed revisions within one scheduling decision.
- [ ] Record author, approver, provenance, signature, activation time, superseded revision, and rollback lineage.
- [ ] Support dry-run/shadow evaluation against live telemetry before a revision can affect placement.
- [ ] Define deterministic precedence for global, environment, site, hardware-class, and node-specific policy layers.
- [ ] Reject unsigned, expired, revoked, unauthorized, or unsupported policy revisions fail closed.
- [ ] Prove rollback restores both policy and associated derived state without transiently opening capacity.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Atomic policy distribution and activation service.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] policy schema and validator.
- [ ] signed example revisions and provenance record.
- [ ] atomic activation/rollback test evidence.
- [ ] policy authorization matrix.
- [ ] staged rollout/dry-run report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 06. Policy authorization/signature verification [P0]

**Traceability:** `C023-C025, C045, C049`  
**Audited gap:** prevent an untrusted actor from raising thermal thresholds, power budgets, or reserve limits.  
**Primary checklist profile:** `security`

### A. Component-specific engineering requirements

- [ ] Require signatures over canonical policy bytes plus immutable metadata such as revision, scope, issuer, issued-at, and expiry.
- [ ] Authorize signers separately for ordinary policy changes versus emergency or capacity-increasing overrides.
- [ ] Use trust roots that can be rotated without accepting unsigned transition windows.
- [ ] Check signer revocation and policy expiry before activation and periodically while active.
- [ ] Prevent threshold/budget/reserve increases from bypassing approval via partial patch, alternate API, old schema, or downgrade.
- [ ] Bind policy signature verification to the exact content digest consumed by the scheduling kernel.
- [ ] Record failed verification attempts without logging secret key material.
- [ ] Define safe behavior when signature verification, revocation, identity, or time service is unavailable.
- [ ] Test forged signatures, wrong audience/scope, expired signatures, revoked signers, replayed old revisions, and version downgrade.
- [ ] Prove unauthorized users cannot increase available capacity through any administrative or configuration interface.

### B. Architecture, security, resilience, and operability

- [ ] Define assets, trust boundaries, identities, attacker capabilities, abuse cases, and security invariants in the GAP-10 threat model.
- [ ] Use workload- or service-scoped identity with least privilege and deny ambient filesystem, network, device, and secret authority.
- [ ] Authenticate every control-plane peer before accepting safety-relevant data or commands.
- [ ] Authorize every privileged operation against explicit capabilities or roles; authentication alone is insufficient.
- [ ] Use modern authenticated transport and managed key rotation; reject insecure downgrade paths.
- [ ] Define revocation behavior and maximum exposure window for compromised credentials or signing keys.
- [ ] Protect against replay with bounded freshness, nonce/sequence/revision checks, and monotonic state where applicable.
- [ ] Keep raw secrets out of logs, metrics, traces, crash dumps, diagnostic bundles, and normal configuration files.
- [ ] Emit tamper-evident audit records for authentication failures, authorization denials, trust changes, and administrative actions.
- [ ] Run adversarial tests for spoofing, replay, privilege escalation, parser abuse, resource exhaustion, and malicious downgrade attempts.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Policy authorization/signature verification.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] threat-model update.
- [ ] identity/capability matrix.
- [ ] key/secret lifecycle runbook.
- [ ] adversarial test report.
- [ ] tamper-evident audit evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 07. Explicit fail-closed scheduler behavior when GAP-10 is absent/unhealthy [P0]

**Traceability:** `C014, C048, C054-C059`  
**Audited gap:** downstream consumers must never interpret missing GAP-10 output as unlimited node capacity.  
**Primary checklist profile:** `control`

### A. Component-specific engineering requirements

- [ ] Define the scheduler behavior when GAP-10 is unreachable, unready, stale, returns invalid data, or has no record for a node.
- [ ] Choose an explicit conservative ceiling/exclusion state for each failure mode and encode it in the downstream contract.
- [ ] Ensure cached last-known-good data expires according to freshness policy and cannot remain authoritative indefinitely.
- [ ] Distinguish “GAP-10 absent” from “nominal” in scheduler state and telemetry.
- [ ] Disable any scheduler fallback that assumes full node allocatable capacity after timeout or component restart.
- [ ] Apply fail-closed behavior consistently across ordinary admission, rescheduling, autoscaling, maintenance drains, and manual operations.
- [ ] Provide a controlled emergency override only through authenticated, audited, expiring policy with explicit risk acceptance.
- [ ] Alert before widespread fail-closed behavior exhausts fleet capacity, without weakening enforcement automatically.
- [ ] Run kill/restart/network-partition tests while placements are in flight.
- [ ] Prove every GAP-10 failure class either preserves the last still-valid restrictive ceiling or transitions to an equal/more restrictive state.

### B. Architecture, security, resilience, and operability

- [ ] Define the control state machine with legal transitions, terminal states, and fail-closed defaults.
- [ ] Require authenticated and authorized control requests with an actor identity, reason, ticket/reference, and expiry where applicable.
- [ ] Make every control operation idempotent and safe under retries, duplicated delivery, and controller failover.
- [ ] Use fencing or generation numbers so stale controllers cannot overwrite newer decisions.
- [ ] Define emergency behavior that monotonically restricts capacity; emergency controls must never implicitly reopen capacity.
- [ ] Provide explicit acknowledgement and downstream confirmation when a control action must propagate to enforcement points.
- [ ] Record every transition in an append-only audit trail with before/after state and policy revision.
- [ ] Expose current control mode, owner, generation, age, and last transition reason in health/explain output.
- [ ] Provide bounded manual recovery steps and two-person approval for high-risk capacity-increasing overrides where policy requires it.
- [ ] Test concurrent commands, stale commands, expired commands, rollback, process crash, and partial downstream acknowledgement.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Explicit fail-closed scheduler behavior when GAP-10 is absent/unhealthy.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] control state-machine specification.
- [ ] authorization matrix.
- [ ] audit-event examples.
- [ ] failover/concurrency test report.
- [ ] operator runbook with recovery gates.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 08. Controller ownership/leader fencing [P0]

**Traceability:** `C057-C059`  
**Audited gap:** avoid two schedulers/controllers simultaneously publishing conflicting ceilings for the same node.  
**Primary checklist profile:** `control`

### A. Component-specific engineering requirements

- [ ] Assign each node/control shard exactly one active ceiling publisher at a time using a lease plus monotonically increasing fencing token.
- [ ] Require downstream consumers to reject publications carrying a fencing token older than the latest accepted owner generation.
- [ ] Define lease duration, renewal interval, maximum clock assumptions, and behavior when the backing coordination service is unavailable.
- [ ] Ensure an isolated old leader cannot continue publishing capacity after losing ownership.
- [ ] Persist enough ownership metadata to reconcile safely after controller crash or coordination-store recovery.
- [ ] Handle node moves between shards/controllers without a window of dual unfenced authority.
- [ ] Expose owner ID, generation/fence, lease age, renewal status, and conflict count.
- [ ] Audit every ownership acquisition, loss, forced transfer, and conflict.
- [ ] Test simultaneous startup, delayed network packets, store partitions, clock skew, stale leader recovery, and rapid failover.
- [ ] Prove split-brain cannot produce a higher applied ceiling than the most restrictive valid publisher.

### B. Architecture, security, resilience, and operability

- [ ] Define the control state machine with legal transitions, terminal states, and fail-closed defaults.
- [ ] Require authenticated and authorized control requests with an actor identity, reason, ticket/reference, and expiry where applicable.
- [ ] Make every control operation idempotent and safe under retries, duplicated delivery, and controller failover.
- [ ] Use fencing or generation numbers so stale controllers cannot overwrite newer decisions.
- [ ] Define emergency behavior that monotonically restricts capacity; emergency controls must never implicitly reopen capacity.
- [ ] Provide explicit acknowledgement and downstream confirmation when a control action must propagate to enforcement points.
- [ ] Record every transition in an append-only audit trail with before/after state and policy revision.
- [ ] Expose current control mode, owner, generation, age, and last transition reason in health/explain output.
- [ ] Provide bounded manual recovery steps and two-person approval for high-risk capacity-increasing overrides where policy requires it.
- [ ] Test concurrent commands, stale commands, expired commands, rollback, process crash, and partial downstream acknowledgement.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Controller ownership/leader fencing.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] control state-machine specification.
- [ ] authorization matrix.
- [ ] audit-event examples.
- [ ] failover/concurrency test report.
- [ ] operator runbook with recovery gates.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 09. Hardware/site calibration inventory [P1]

**Traceability:** `C012, C017, C031, C035`  
**Audited gap:** validated per-device temperature limits, sustained/TDP power budgets, battery chemistry/reserve rules, and cooling characteristics.  
**Primary checklist profile:** `model`

### A. Component-specific engineering requirements

- [ ] Create a signed inventory keyed by stable hardware identity/SKU/firmware containing supported temperature limits and power characteristics.
- [ ] Record sustained/TDP/PL1/PL2 or vendor-equivalent limits separately; do not conflate instantaneous and sustained power budgets.
- [ ] Capture battery chemistry, design capacity, current health/cycle state, reserve requirements, and supported discharge characteristics.
- [ ] Record cooling topology, fan/cooling capability, inlet constraints, thermal design assumptions, and site derating factors.
- [ ] Distinguish vendor absolute maximums from operational safety thresholds and document safety margin rationale.
- [ ] Version calibration entries and bind every GAP-10 decision to the calibration revision used.
- [ ] Reject unknown or ambiguous hardware classes into conservative defaults until calibrated.
- [ ] Define revalidation triggers for firmware, BIOS, sensor-provider, battery, cooling, or hardware changes.
- [ ] Provide calibration verification tests against actual sensor providers and device telemetry.
- [ ] Audit changes to limits that could increase permitted capacity.

### B. Architecture, security, resilience, and operability

- [ ] Define physical quantities, units, sampling assumptions, calibration ranges, and invalid-value handling explicitly.
- [ ] Document whether each model is conservative, worst-case, weighted, predictive, or probabilistic and why that is safe.
- [ ] Establish deterministic behavior at exact threshold boundaries and around hysteresis margins.
- [ ] Define missing-sensor, stale-sensor, disagreement, outlier, saturation, and impossible-value semantics.
- [ ] Use monotonic or conservative transformations so model uncertainty cannot increase allowed capacity accidentally.
- [ ] Separate raw measurement, normalized measurement, derived feature, model output, and final ceiling decision in code and telemetry.
- [ ] Version calibration/model parameters independently from executable code and bind decisions to the active revision.
- [ ] Quantify numerical stability, precision, rounding, and overflow/underflow behavior for all supported runtimes.
- [ ] Provide golden-vector fixtures covering nominal, boundary, emergency, degraded, and contradictory evidence scenarios.
- [ ] Validate predictions/estimates against measured hardware or replay datasets and define acceptable error envelopes.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Hardware/site calibration inventory.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] model/calibration specification with units.
- [ ] golden vectors.
- [ ] hardware/replay validation dataset summary.
- [ ] error/uncertainty analysis.
- [ ] boundary and degraded-mode test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 10. Multi-sensor aggregation model [P1]

**Traceability:** `C011-C015`  
**Audited gap:** combine CPU, GPU, VRM, SSD, inlet, exhaust, chassis, and accelerator hotspot sensors using an explicit worst-case or weighted policy.  
**Primary checklist profile:** `model`

### A. Component-specific engineering requirements

- [ ] Enumerate CPU package/core, GPU hotspot/memory, VRM, SSD/NVMe, inlet, exhaust, chassis, PSU, accelerator, and vendor-specific sensors per hardware class.
- [ ] Define canonical sensor IDs, units, expected ranges, criticality, sampling cadence, and trust level.
- [ ] Choose explicit worst-case/weighted/domain aggregation rules and document why the rule cannot hide a dangerous hotspot.
- [ ] Treat missing required sensors separately from optional sensors and define conservative substitution behavior.
- [ ] Detect sensor disagreement, stuck values, implausible jumps, saturation, and duplicated sensor streams.
- [ ] Account for different sensor lag/response times when combining fast hotspot and slow ambient readings.
- [ ] Prevent averaging from lowering the effective severity below the most safety-critical sensor where policy forbids it.
- [ ] Expose the full contributing-sensor set and winning constraint in explain output.
- [ ] Build golden fixtures for one-hot hotspots, conflicting sensors, missing sensors, stale substreams, and simultaneous thermal/power events.
- [ ] Validate aggregation against real hardware traces for each supported class.

### B. Architecture, security, resilience, and operability

- [ ] Define physical quantities, units, sampling assumptions, calibration ranges, and invalid-value handling explicitly.
- [ ] Document whether each model is conservative, worst-case, weighted, predictive, or probabilistic and why that is safe.
- [ ] Establish deterministic behavior at exact threshold boundaries and around hysteresis margins.
- [ ] Define missing-sensor, stale-sensor, disagreement, outlier, saturation, and impossible-value semantics.
- [ ] Use monotonic or conservative transformations so model uncertainty cannot increase allowed capacity accidentally.
- [ ] Separate raw measurement, normalized measurement, derived feature, model output, and final ceiling decision in code and telemetry.
- [ ] Version calibration/model parameters independently from executable code and bind decisions to the active revision.
- [ ] Quantify numerical stability, precision, rounding, and overflow/underflow behavior for all supported runtimes.
- [ ] Provide golden-vector fixtures covering nominal, boundary, emergency, degraded, and contradictory evidence scenarios.
- [ ] Validate predictions/estimates against measured hardware or replay datasets and define acceptable error envelopes.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Multi-sensor aggregation model.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] model/calibration specification with units.
- [ ] golden vectors.
- [ ] hardware/replay validation dataset summary.
- [ ] error/uncertainty analysis.
- [ ] boundary and degraded-mode test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 11. Thermal rate-of-rise predictor [P1]

**Traceability:** `C013, C061-C070`  
**Audited gap:** predictive derating before the static threshold is crossed, required to substantiate the stated 99% pre-throttle SLO.  
**Primary checklist profile:** `model`

### A. Component-specific engineering requirements

- [ ] Compute temperature derivative/rate-of-rise over a defined robust time window using trusted samples only.
- [ ] Define filtering/smoothing that reduces noise without delaying recognition of a genuine fast rise beyond the safety budget.
- [ ] Derive predicted time-to-threshold for elevated, critical, and emergency boundaries.
- [ ] Incorporate current power draw/load trend where available so prediction responds to changing heat input.
- [ ] Define conservative fallback when there are too few samples, irregular cadence, gaps, or clock anomalies.
- [ ] Bound prediction horizon and model output so extrapolation cannot create unjustified capacity increases.
- [ ] Make predictive derating monotonic: increasing risk may restrict capacity earlier but prediction failure cannot relax static safety rules.
- [ ] Calibrate model error by hardware class and environmental condition; publish confidence/error envelopes.
- [ ] Measure the claimed pre-throttle objective using replay/bench traces and define numerator/denominator precisely.
- [ ] Test abrupt workload spikes, sensor noise, cooling recovery, slow drift, missing samples, and false-positive control.

### B. Architecture, security, resilience, and operability

- [ ] Define physical quantities, units, sampling assumptions, calibration ranges, and invalid-value handling explicitly.
- [ ] Document whether each model is conservative, worst-case, weighted, predictive, or probabilistic and why that is safe.
- [ ] Establish deterministic behavior at exact threshold boundaries and around hysteresis margins.
- [ ] Define missing-sensor, stale-sensor, disagreement, outlier, saturation, and impossible-value semantics.
- [ ] Use monotonic or conservative transformations so model uncertainty cannot increase allowed capacity accidentally.
- [ ] Separate raw measurement, normalized measurement, derived feature, model output, and final ceiling decision in code and telemetry.
- [ ] Version calibration/model parameters independently from executable code and bind decisions to the active revision.
- [ ] Quantify numerical stability, precision, rounding, and overflow/underflow behavior for all supported runtimes.
- [ ] Provide golden-vector fixtures covering nominal, boundary, emergency, degraded, and contradictory evidence scenarios.
- [ ] Validate predictions/estimates against measured hardware or replay datasets and define acceptable error envelopes.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Thermal rate-of-rise predictor.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] model/calibration specification with units.
- [ ] golden vectors.
- [ ] hardware/replay validation dataset summary.
- [ ] error/uncertainty analysis.
- [ ] boundary and degraded-mode test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 12. Battery discharge/remaining-runtime estimator [P1]

**Traceability:** `C017, C068-C069`  
**Audited gap:** use load, battery health, discharge curve, reserve target, and expected runtime instead of a single remaining-fraction threshold.  
**Primary checklist profile:** `model`

### A. Component-specific engineering requirements

- [ ] Estimate remaining energy using design/full-charge capacity, current state of charge, health, temperature, and battery telemetry quality.
- [ ] Estimate discharge power from current load rather than treating remaining fraction as a direct runtime proxy.
- [ ] Produce remaining-runtime estimate plus conservative lower bound under the current/expected workload.
- [ ] Account for battery degradation, temperature-dependent capacity, inverter/UPS efficiency, and configured reserve.
- [ ] Define reserve in both energy/time terms where operational requirements demand minimum shutdown or migration time.
- [ ] Handle charging, discharging, unknown direction, sensor reset, pack replacement, and mixed battery/utility states explicitly.
- [ ] Prevent optimistic runtime recovery from one transient low-load sample by applying hysteresis/smoothing.
- [ ] Expose inputs, model revision, estimated runtime, reserve margin, and uncertainty in explain output.
- [ ] Validate estimates against controlled discharge traces per battery chemistry/hardware class.
- [ ] Test sudden power increase, degraded-health pack, stale battery telemetry, pack swap, and transition to utility power.

### B. Architecture, security, resilience, and operability

- [ ] Define physical quantities, units, sampling assumptions, calibration ranges, and invalid-value handling explicitly.
- [ ] Document whether each model is conservative, worst-case, weighted, predictive, or probabilistic and why that is safe.
- [ ] Establish deterministic behavior at exact threshold boundaries and around hysteresis margins.
- [ ] Define missing-sensor, stale-sensor, disagreement, outlier, saturation, and impossible-value semantics.
- [ ] Use monotonic or conservative transformations so model uncertainty cannot increase allowed capacity accidentally.
- [ ] Separate raw measurement, normalized measurement, derived feature, model output, and final ceiling decision in code and telemetry.
- [ ] Version calibration/model parameters independently from executable code and bind decisions to the active revision.
- [ ] Quantify numerical stability, precision, rounding, and overflow/underflow behavior for all supported runtimes.
- [ ] Provide golden-vector fixtures covering nominal, boundary, emergency, degraded, and contradictory evidence scenarios.
- [ ] Validate predictions/estimates against measured hardware or replay datasets and define acceptable error envelopes.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Battery discharge/remaining-runtime estimator.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] model/calibration specification with units.
- [ ] golden vectors.
- [ ] hardware/replay validation dataset summary.
- [ ] error/uncertainty analysis.
- [ ] boundary and degraded-mode test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 13. Cooling-domain/site correlation [P1]

**Traceability:** `C006, C055, C068-C069`  
**Audited gap:** model shared racks/cabinets/rooms so a local cool reading does not hide a failing shared cooling domain.  
**Primary checklist profile:** `model`

### A. Component-specific engineering requirements

- [ ] Model rack/cabinet/room/cooling-loop membership as versioned topology rather than inferring it from node names.
- [ ] Define domain-level signals such as inlet temperature, exhaust temperature, CRAC/chiller status, fan state, power density, and aggregate heat load.
- [ ] Propagate a shared cooling-domain constraint to all affected nodes even if an individual node sensor remains nominal.
- [ ] Define conservative behavior when topology membership or domain telemetry is missing, stale, or conflicting.
- [ ] Prevent correlated failures from being treated as independent capacity across nodes sharing the same cooling bottleneck.
- [ ] Include maintenance/outage state for shared cooling equipment in the domain constraint model.
- [ ] Integrate site power availability and cooling capacity where a combined facility limit is required.
- [ ] Expose domain ID, active domain constraint, contributing signals, and affected node count.
- [ ] Test fan/chiller failure, hot-aisle recirculation, partial rack telemetry loss, domain split/merge, and site partition.
- [ ] Validate that local recovery does not reopen nodes until shared-domain recovery criteria are also met.

### B. Architecture, security, resilience, and operability

- [ ] Define physical quantities, units, sampling assumptions, calibration ranges, and invalid-value handling explicitly.
- [ ] Document whether each model is conservative, worst-case, weighted, predictive, or probabilistic and why that is safe.
- [ ] Establish deterministic behavior at exact threshold boundaries and around hysteresis margins.
- [ ] Define missing-sensor, stale-sensor, disagreement, outlier, saturation, and impossible-value semantics.
- [ ] Use monotonic or conservative transformations so model uncertainty cannot increase allowed capacity accidentally.
- [ ] Separate raw measurement, normalized measurement, derived feature, model output, and final ceiling decision in code and telemetry.
- [ ] Version calibration/model parameters independently from executable code and bind decisions to the active revision.
- [ ] Quantify numerical stability, precision, rounding, and overflow/underflow behavior for all supported runtimes.
- [ ] Provide golden-vector fixtures covering nominal, boundary, emergency, degraded, and contradictory evidence scenarios.
- [ ] Validate predictions/estimates against measured hardware or replay datasets and define acceptable error envelopes.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Cooling-domain/site correlation.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] model/calibration specification with units.
- [ ] golden vectors.
- [ ] hardware/replay validation dataset summary.
- [ ] error/uncertainty analysis.
- [ ] boundary and degraded-mode test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 14. Accelerator thermal integration with GAP-11 [P1]

**Traceability:** `C003, C030, C068`  
**Audited gap:** GPU/NPU/FPGA power and hotspot contribution integrated into node ceilings.  
**Primary checklist profile:** `adapter`

### A. Component-specific engineering requirements

- [ ] Consume GAP-11 accelerator inventory, allocation, hotspot temperature, power draw, power cap, and health using a versioned authenticated contract.
- [ ] Normalize GPU/NPU/FPGA vendor telemetry into canonical accelerator constraints without losing device identity.
- [ ] Associate accelerator devices with the correct node, workload allocation, power rail, and cooling domain.
- [ ] Include accelerator hotspot and aggregate board power in the most-restrictive-wins node ceiling calculation.
- [ ] Define behavior for accelerator telemetry loss while host CPU telemetry remains healthy.
- [ ] Prevent scheduler placement onto an excluded accelerator while allowing safe non-accelerator capacity only if policy explicitly supports it.
- [ ] Handle multi-accelerator nodes where one device is critical and others are nominal.
- [ ] Propagate accelerator-caused ceilings to GAP-11 scheduling/admission paths as well as general node scheduling.
- [ ] Provide cross-component decision IDs so a GAP-10 ceiling can be traced to the exact GAP-11 sample/device.
- [ ] Test device reset, MIG/partition reconfiguration, hot-unplug, mixed vendors, power-cap changes, and schema-version skew.

### B. Architecture, security, resilience, and operability

- [ ] Define the adapter boundary as a separately testable module with no implicit ambient authority or hidden transport assumptions.
- [ ] Version every inbound and outbound message contract and reject unsupported major schema versions deterministically.
- [ ] Normalize peer-specific payloads into canonical GAP-10 domain objects before any scheduling decision is evaluated.
- [ ] Preserve source identity, correlation IDs, evidence timestamps, trust state, and policy revision across translation.
- [ ] Make duplicate delivery idempotent and prove that retries cannot multiply side effects or relax a ceiling.
- [ ] Bound connection pools, outstanding RPCs, payload sizes, decode time, queue depth, and per-peer concurrency.
- [ ] Specify explicit timeout, cancellation, retry, and backpressure behavior for every remote operation.
- [ ] Fail closed on malformed, unauthenticated, stale, ambiguous, or unsupported peer data.
- [ ] Expose peer compatibility, negotiated version, last-success time, and current degraded mode through health telemetry.
- [ ] Provide contract fixtures for nominal, boundary, malformed, stale, replayed, downgraded, and emergency cases.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Accelerator thermal integration with GAP-11.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] versioned adapter schema/contracts.
- [ ] positive and negative interoperability fixtures.
- [ ] integration test report with peer versions and applied outcomes.
- [ ] adapter health/metrics specification.
- [ ] security/authentication test evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 15. Workload-class-aware shedding policy [P1]

**Traceability:** `C017, optional contract capability`  
**Audited gap:** deterministic rules for which capacity classes are reduced first without allowing any class to bypass emergency exclusion.  
**Primary checklist profile:** `policy`

### A. Component-specific engineering requirements

- [ ] Define workload classes using explicit policy attributes, not application-supplied free-form priority alone.
- [ ] Specify deterministic shedding order for best-effort, batch, latency-sensitive, control-plane, safety-critical, and protected workloads as applicable.
- [ ] Keep emergency node exclusion absolute unless a separately designed life/safety exception exists and is formally approved.
- [ ] Define how quotas, fairness, disruption budgets, tenant isolation, and protected minimums interact with thermal shedding.
- [ ] Prevent a tenant from self-classifying into a protected class without authorization.
- [ ] Use stable tie-breakers so identical state yields identical shedding decisions.
- [ ] Define whether shedding means no-new-admission, throttling, migration, eviction, pause, or termination per workload class.
- [ ] Expose the class rule and precedence path that caused each action.
- [ ] Test starvation/fairness over prolonged constrained periods and recovery ordering when capacity returns.
- [ ] Prove workload class can change which capacity is shed first but cannot bypass a critical/emergency safety ceiling.

### B. Architecture, security, resilience, and operability

- [ ] Represent policy as a versioned immutable document with a unique revision ID and content digest.
- [ ] Define an explicit schema covering thresholds, hysteresis, ceilings, reserve rules, scope selectors, and emergency behavior.
- [ ] Validate ordering invariants, units, numeric ranges, mandatory zero-capacity emergency semantics, and cross-field constraints before activation.
- [ ] Separate policy authoring, approval, distribution, activation, and rollback roles.
- [ ] Make activation atomic per declared scope and prevent mixed revisions within one scheduling decision.
- [ ] Record author, approver, provenance, signature, activation time, superseded revision, and rollback lineage.
- [ ] Support dry-run/shadow evaluation against live telemetry before a revision can affect placement.
- [ ] Define deterministic precedence for global, environment, site, hardware-class, and node-specific policy layers.
- [ ] Reject unsigned, expired, revoked, unauthorized, or unsupported policy revisions fail closed.
- [ ] Prove rollback restores both policy and associated derived state without transiently opening capacity.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Workload-class-aware shedding policy.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] policy schema and validator.
- [ ] signed example revisions and provenance record.
- [ ] atomic activation/rollback test evidence.
- [ ] policy authorization matrix.
- [ ] staged rollout/dry-run report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 16. Constraint-precedence engine [P1]

**Traceability:** `C019`  
**Audited gap:** documented and executable precedence among thermal safety, security, residency, SLO, cost, maintenance, and emergency operator actions.  
**Primary checklist profile:** `policy`

### A. Component-specific engineering requirements

- [ ] Enumerate constraints including thermal safety, power, battery reserve, security/isolation, residency, availability/SLO, maintenance, operator emergency action, and cost.
- [ ] Classify each constraint as hard, soft, advisory, or optimization-only with explicit justification.
- [ ] Define deterministic precedence and composition rules for every pair of potentially conflicting hard constraints.
- [ ] Implement “most restrictive wins” for safety ceilings unless an ADR explicitly defines a safer specialized rule.
- [ ] Detect unsatisfiable constraint sets and return a structured terminal/degraded decision rather than silently dropping constraints.
- [ ] Prevent cost or utilization objectives from overriding safety/security/residency hard constraints.
- [ ] Version the precedence policy and bind each decision to the active revision.
- [ ] Generate an explain tree showing evaluated constraints, precedence, winner, and rejected alternatives.
- [ ] Create exhaustive truth-table/property tests for boundary combinations and contradictory constraints.
- [ ] Require architecture/security approval for any precedence change that can increase schedulable capacity.

### B. Architecture, security, resilience, and operability

- [ ] Represent policy as a versioned immutable document with a unique revision ID and content digest.
- [ ] Define an explicit schema covering thresholds, hysteresis, ceilings, reserve rules, scope selectors, and emergency behavior.
- [ ] Validate ordering invariants, units, numeric ranges, mandatory zero-capacity emergency semantics, and cross-field constraints before activation.
- [ ] Separate policy authoring, approval, distribution, activation, and rollback roles.
- [ ] Make activation atomic per declared scope and prevent mixed revisions within one scheduling decision.
- [ ] Record author, approver, provenance, signature, activation time, superseded revision, and rollback lineage.
- [ ] Support dry-run/shadow evaluation against live telemetry before a revision can affect placement.
- [ ] Define deterministic precedence for global, environment, site, hardware-class, and node-specific policy layers.
- [ ] Reject unsigned, expired, revoked, unauthorized, or unsupported policy revisions fail closed.
- [ ] Prove rollback restores both policy and associated derived state without transiently opening capacity.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Constraint-precedence engine.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] policy schema and validator.
- [ ] signed example revisions and provenance record.
- [ ] atomic activation/rollback test evidence.
- [ ] policy authorization matrix.
- [ ] staged rollout/dry-run report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 17. Health/readiness API [P1]

**Traceability:** `C052, C071`  
**Audited gap:** expose active policy revision, sample age, dependency health, state-store health, and whether the component is safe to enforce.  
**Primary checklist profile:** `api`

### A. Component-specific engineering requirements

- [ ] Expose liveness separately from readiness; a process may be alive while unsafe to enforce.
- [ ] Report active code version, schema versions, policy revision, calibration revision, ownership generation, and capability set.
- [ ] Report telemetry freshness/trust status, state-store health, policy service health, scheduler/elasticity connectivity, and time-service status.
- [ ] Define readiness as false when any safety-critical dependency or invariant is unavailable, stale, invalid, or conflicting.
- [ ] Include reason codes and timestamps for every degraded/unready state.
- [ ] Protect detailed health output by authorization when it reveals infrastructure topology or security state.
- [ ] Rate-limit probes and ensure health checking cannot starve scheduling work.
- [ ] Publish machine-readable health suitable for orchestration plus operator-readable diagnostic detail.
- [ ] Test dependency flapping and apply readiness hysteresis/debounce without masking real unsafe states.
- [ ] Prove downstream components react to unready GAP-10 according to fail-closed semantics.

### B. Architecture, security, resilience, and operability

- [ ] Define the endpoint or service contract using a versioned schema with explicit request, response, and error types.
- [ ] Document authentication, authorization, scope, and information-disclosure rules for every operation.
- [ ] Validate all query/path/body fields before processing and enforce strict maximum sizes and cardinalities.
- [ ] Return stable machine-readable error codes rather than relying on free-form error text.
- [ ] Define cacheability, consistency, freshness, and pagination/streaming semantics where applicable.
- [ ] Prevent the interface from exposing secrets, raw credentials, unredacted tenant data, or unnecessary infrastructure details.
- [ ] Use rate limiting, concurrency limits, timeouts, and cancellation to protect the control plane.
- [ ] Provide deterministic reference examples and negative fixtures for malformed and unauthorized requests.
- [ ] Instrument request count, error count, latency distribution, saturation, and dependency failures.
- [ ] Create contract, compatibility, security, and load tests for every supported API version.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Health/readiness API.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] OpenAPI/JSON Schema/RPC contract or equivalent.
- [ ] RBAC/capability matrix.
- [ ] contract and negative fixtures.
- [ ] load/rate-limit test report.
- [ ] security/privacy review.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 18. Quarantine/freeze/emergency-disable control [P1]

**Traceability:** `C059, C092`  
**Audited gap:** authenticated operational control that is observable, reversible, and cannot silently revert to unlimited capacity.  
**Primary checklist profile:** `control`

### A. Component-specific engineering requirements

- [ ] Define distinct modes for quarantine, freeze, emergency-disable/exclusion, and controlled maintenance; do not overload one ambiguous flag.
- [ ] Ensure every mode has explicit effects on new admission, existing workloads, ceiling publication, policy updates, and recovery.
- [ ] Require authenticated/authorized actor, reason, scope, ticket/reference, and optional expiry for manual controls.
- [ ] Default ambiguous emergency actions toward restricting capacity rather than enabling it.
- [ ] Make capacity-increasing release from quarantine/freeze an explicit separate action with validation gates.
- [ ] Propagate control state to scheduler and elasticity enforcement and verify acknowledgement.
- [ ] Persist control state durably so process restart cannot clear an active safety action.
- [ ] Expose current mode and origin in health/explain/UI and emit alerts for long-lived manual controls.
- [ ] Audit every create/update/clear attempt including denied actions.
- [ ] Test stale operator sessions, duplicate commands, partial downstream failure, controller failover, expiry, and emergency rollback.

### B. Architecture, security, resilience, and operability

- [ ] Define the control state machine with legal transitions, terminal states, and fail-closed defaults.
- [ ] Require authenticated and authorized control requests with an actor identity, reason, ticket/reference, and expiry where applicable.
- [ ] Make every control operation idempotent and safe under retries, duplicated delivery, and controller failover.
- [ ] Use fencing or generation numbers so stale controllers cannot overwrite newer decisions.
- [ ] Define emergency behavior that monotonically restricts capacity; emergency controls must never implicitly reopen capacity.
- [ ] Provide explicit acknowledgement and downstream confirmation when a control action must propagate to enforcement points.
- [ ] Record every transition in an append-only audit trail with before/after state and policy revision.
- [ ] Expose current control mode, owner, generation, age, and last transition reason in health/explain output.
- [ ] Provide bounded manual recovery steps and two-person approval for high-risk capacity-increasing overrides where policy requires it.
- [ ] Test concurrent commands, stale commands, expired commands, rollback, process crash, and partial downstream acknowledgement.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Quarantine/freeze/emergency-disable control.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] control state-machine specification.
- [ ] authorization matrix.
- [ ] audit-event examples.
- [ ] failover/concurrency test report.
- [ ] operator runbook with recovery gates.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 19. Structured error taxonomy [P2]

**Traceability:** `C026`  
**Audited gap:** stable machine-readable error codes for invalid policy, stale telemetry, missing trust, store failure, ownership conflict, and downstream rejection.  
**Primary checklist profile:** `api`

### A. Component-specific engineering requirements

- [ ] Define a stable namespaced error-code catalog partitioned by validation, trust, telemetry, policy, storage, ownership, dependency, enforcement, and internal failures.
- [ ] Assign retryability, severity, HTTP/RPC mapping, operator action, and safe fallback to every error code.
- [ ] Include structured details such as node ID, dependency, policy revision, sample age, and rejected field only when safe to disclose.
- [ ] Keep human-readable messages non-authoritative; automation must branch on stable codes/fields.
- [ ] Define compatibility rules so adding new error codes is backward compatible and removing/redefining codes requires major versioning.
- [ ] Never encode secrets or raw signed payloads in error details.
- [ ] Preserve root-cause chains across adapters without leaking peer-specific internals unnecessarily.
- [ ] Map all current model validation/freshness/replay states into the taxonomy.
- [ ] Add negative contract tests asserting exact codes for malformed, stale, replayed, unauthorized, ownership-conflict, and downstream-rejection cases.
- [ ] Generate documentation directly from the machine-readable error catalog to prevent drift.

### B. Architecture, security, resilience, and operability

- [ ] Define the endpoint or service contract using a versioned schema with explicit request, response, and error types.
- [ ] Document authentication, authorization, scope, and information-disclosure rules for every operation.
- [ ] Validate all query/path/body fields before processing and enforce strict maximum sizes and cardinalities.
- [ ] Return stable machine-readable error codes rather than relying on free-form error text.
- [ ] Define cacheability, consistency, freshness, and pagination/streaming semantics where applicable.
- [ ] Prevent the interface from exposing secrets, raw credentials, unredacted tenant data, or unnecessary infrastructure details.
- [ ] Use rate limiting, concurrency limits, timeouts, and cancellation to protect the control plane.
- [ ] Provide deterministic reference examples and negative fixtures for malformed and unauthorized requests.
- [ ] Instrument request count, error count, latency distribution, saturation, and dependency failures.
- [ ] Create contract, compatibility, security, and load tests for every supported API version.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Structured error taxonomy.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] OpenAPI/JSON Schema/RPC contract or equivalent.
- [ ] RBAC/capability matrix.
- [ ] contract and negative fixtures.
- [ ] load/rate-limit test report.
- [ ] security/privacy review.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 20. Tamper-evident audit sink [P2]

**Traceability:** `C049`  
**Audited gap:** append-only records for policy changes, emergency exclusions, overrides, ownership changes, and security failures.  
**Primary checklist profile:** `security`

### A. Component-specific engineering requirements

- [ ] Use an append-only or cryptographically tamper-evident sink with ordered event identifiers and integrity verification.
- [ ] Capture policy author/approval/activation/rollback, emergency controls, ownership changes, trust failures, overrides, and production-gate actions.
- [ ] Include actor/service identity, target scope, before/after state digest, policy/build revision, timestamp, and correlation ID.
- [ ] Use a trusted timestamp strategy and define behavior when time trust is degraded.
- [ ] Protect audit writes from ordinary service credentials being able to rewrite/delete history.
- [ ] Define buffering/backpressure so temporary audit-sink failure does not silently lose security events.
- [ ] Define which operations must fail closed if their audit event cannot be durably recorded.
- [ ] Encrypt sensitive audit data and restrict read access separately from write authority.
- [ ] Provide retention, export, legal/compliance, integrity-check, and restoration procedures.
- [ ] Test event-loss detection, ordering, duplicate submission, sink outage, key rotation, and integrity-verification failure.

### B. Architecture, security, resilience, and operability

- [ ] Define assets, trust boundaries, identities, attacker capabilities, abuse cases, and security invariants in the GAP-10 threat model.
- [ ] Use workload- or service-scoped identity with least privilege and deny ambient filesystem, network, device, and secret authority.
- [ ] Authenticate every control-plane peer before accepting safety-relevant data or commands.
- [ ] Authorize every privileged operation against explicit capabilities or roles; authentication alone is insufficient.
- [ ] Use modern authenticated transport and managed key rotation; reject insecure downgrade paths.
- [ ] Define revocation behavior and maximum exposure window for compromised credentials or signing keys.
- [ ] Protect against replay with bounded freshness, nonce/sequence/revision checks, and monotonic state where applicable.
- [ ] Keep raw secrets out of logs, metrics, traces, crash dumps, diagnostic bundles, and normal configuration files.
- [ ] Emit tamper-evident audit records for authentication failures, authorization denials, trust changes, and administrative actions.
- [ ] Run adversarial tests for spoofing, replay, privilege escalation, parser abuse, resource exhaustion, and malicious downgrade attempts.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Tamper-evident audit sink.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] threat-model update.
- [ ] identity/capability matrix.
- [ ] key/secret lifecycle runbook.
- [ ] adversarial test report.
- [ ] tamper-evident audit evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 21. Metrics exporter [P2]

**Traceability:** `C072`  
**Audited gap:** gauges/counters/histograms for temperature, power ratio, ceiling, exclusions, telemetry age, hysteresis holds, decision latency, and dependency failures.  
**Primary checklist profile:** `observability`

### A. Component-specific engineering requirements

- [ ] Export current temperature by sensor/domain, power draw/budget ratio, battery/runtime reserve, selected band, ceiling fraction, and exclusion state.
- [ ] Count state transitions, emergency exclusions, hysteresis holds, stale samples, future samples, replay rejects, invalid samples, and trust failures.
- [ ] Measure decision latency and dependency latency with p50/p95/p99 histograms using consistent units/buckets.
- [ ] Expose state-store, policy-service, GAP-09, GAP-11, scheduler, elasticity, and time-service availability/error counters.
- [ ] Export desired versus applied downstream ceiling and enforcement lag.
- [ ] Bound labels to site/node/hardware class/component/reason-code dimensions approved for cardinality.
- [ ] Avoid raw workload IDs in default metrics; use traces/logs for high-cardinality diagnosis.
- [ ] Define metric reset/restart semantics and distinguish counters from gauges.
- [ ] Provide recording rules for fleet-level thermal pressure, excluded-capacity percentage, and telemetry trust failure rate.
- [ ] Validate metric names, units, label sets, and alert expressions in CI.

### B. Architecture, security, resilience, and operability

- [ ] Define an observability schema with stable names, units, labels, cardinality limits, and privacy classification.
- [ ] Expose rate, error, latency, saturation, backlog, resource use, safety-state, and dependency-health signals where applicable.
- [ ] Attach stable node, site, component, policy revision, decision ID, and operation correlation identifiers.
- [ ] Propagate trace context across GAP-09, GAP-10, scheduler, elasticity, policy, and state-store boundaries.
- [ ] Keep unbounded workload IDs, raw payloads, secrets, and high-cardinality data out of default metric labels.
- [ ] Define metric sampling, retention, aggregation, and export intervals appropriate to safety and operational debugging.
- [ ] Distinguish expected thermal derating from sensor trust failure, software failure, attack rejection, and downstream enforcement failure.
- [ ] Provide SLO-oriented dashboards with clearly documented alert thresholds and runbook links.
- [ ] Test that every safety-critical state transition generates the expected metric/log/trace/audit evidence.
- [ ] Verify observability loss cannot alter decision semantics or make the scheduler interpret missing telemetry as healthy capacity.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Metrics exporter.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] telemetry schema/data dictionary.
- [ ] dashboard definitions.
- [ ] alert rules plus runbooks.
- [ ] trace/log correlation examples.
- [ ] cardinality/privacy validation report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 22. Structured logging and trace propagation [P2]

**Traceability:** `C073-C075`  
**Audited gap:** stable node/site/workload/operation IDs with privacy-safe high-cardinality diagnostics.  
**Primary checklist profile:** `observability`

### A. Component-specific engineering requirements

- [ ] Define a structured log schema including timestamp, severity, component, node/site, decision ID, policy revision, owner generation, reason codes, and trace/span IDs.
- [ ] Propagate W3C-compatible or estate-standard trace context across telemetry ingestion, decision calculation, state persistence, and downstream enforcement.
- [ ] Create spans for policy lookup, state load/store, model evaluation, ceiling publication, and downstream acknowledgement.
- [ ] Record decision inputs as bounded/redacted summaries rather than dumping raw signed payloads or secrets.
- [ ] Use sampling rules that retain all emergency/security failures while controlling normal high-volume traces.
- [ ] Normalize error taxonomy into logs and trace status so operators can pivot consistently.
- [ ] Prevent attacker-controlled strings from causing log injection or unbounded field cardinality.
- [ ] Define retention/privacy rules for node, site, tenant, workload, and hardware identifiers.
- [ ] Test trace continuity through retries and asynchronous queues.
- [ ] Provide a diagnostic bundle format linking logs/traces/metrics to a decision ID without exposing secret material.

### B. Architecture, security, resilience, and operability

- [ ] Define an observability schema with stable names, units, labels, cardinality limits, and privacy classification.
- [ ] Expose rate, error, latency, saturation, backlog, resource use, safety-state, and dependency-health signals where applicable.
- [ ] Attach stable node, site, component, policy revision, decision ID, and operation correlation identifiers.
- [ ] Propagate trace context across GAP-09, GAP-10, scheduler, elasticity, policy, and state-store boundaries.
- [ ] Keep unbounded workload IDs, raw payloads, secrets, and high-cardinality data out of default metric labels.
- [ ] Define metric sampling, retention, aggregation, and export intervals appropriate to safety and operational debugging.
- [ ] Distinguish expected thermal derating from sensor trust failure, software failure, attack rejection, and downstream enforcement failure.
- [ ] Provide SLO-oriented dashboards with clearly documented alert thresholds and runbook links.
- [ ] Test that every safety-critical state transition generates the expected metric/log/trace/audit evidence.
- [ ] Verify observability loss cannot alter decision semantics or make the scheduler interpret missing telemetry as healthy capacity.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Structured logging and trace propagation.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] telemetry schema/data dictionary.
- [ ] dashboard definitions.
- [ ] alert rules plus runbooks.
- [ ] trace/log correlation examples.
- [ ] cardinality/privacy validation report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 23. Operator explain endpoint/UI [P2]

**Traceability:** `C076-C078`  
**Audited gap:** show current decision, exact source samples, policy revision, threshold crossings, hysteresis state, and downstream enforcement status.  
**Primary checklist profile:** `api`

### A. Component-specific engineering requirements

- [ ] Show the current effective band, ceiling fraction, exclusion state, and whether downstream enforcement has acknowledged it.
- [ ] List exact contributing trusted samples with sensor/source IDs, values, observed times, age, and trust/freshness status.
- [ ] Show active policy and calibration revisions plus the precise thresholds/recovery margins applied.
- [ ] Expose each evaluated constraint and identify the most restrictive winning constraint.
- [ ] Explain hysteresis: previous state, recovery threshold, hold reason, and conditions required to recover.
- [ ] Show controller owner/fence and state-store revision used for the decision.
- [ ] Include scheduler/elasticity desired versus applied state and enforcement lag/error.
- [ ] Protect sensitive topology and tenant/workload detail with role-based access and redaction.
- [ ] Provide immutable decision IDs that can be used to correlate audit, metrics, logs, and traces.
- [ ] Create usability/accuracy tests proving displayed explanations match machine decision records for golden scenarios.

### B. Architecture, security, resilience, and operability

- [ ] Define the endpoint or service contract using a versioned schema with explicit request, response, and error types.
- [ ] Document authentication, authorization, scope, and information-disclosure rules for every operation.
- [ ] Validate all query/path/body fields before processing and enforce strict maximum sizes and cardinalities.
- [ ] Return stable machine-readable error codes rather than relying on free-form error text.
- [ ] Define cacheability, consistency, freshness, and pagination/streaming semantics where applicable.
- [ ] Prevent the interface from exposing secrets, raw credentials, unredacted tenant data, or unnecessary infrastructure details.
- [ ] Use rate limiting, concurrency limits, timeouts, and cancellation to protect the control plane.
- [ ] Provide deterministic reference examples and negative fixtures for malformed and unauthorized requests.
- [ ] Instrument request count, error count, latency distribution, saturation, and dependency failures.
- [ ] Create contract, compatibility, security, and load tests for every supported API version.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Operator explain endpoint/UI.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] OpenAPI/JSON Schema/RPC contract or equivalent.
- [ ] RBAC/capability matrix.
- [ ] contract and negative fixtures.
- [ ] load/rate-limit test report.
- [ ] security/privacy review.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 24. Dashboards and alerts [P2]

**Traceability:** `C080`  
**Audited gap:** distinguish ordinary derating from stale telemetry, cooling failure, battery emergency, forged-input rejection, software defects, and fleet-wide events.  
**Primary checklist profile:** `observability`

### A. Component-specific engineering requirements

- [ ] Create fleet/site/node dashboards for temperature, power ratio, battery reserve, band distribution, excluded capacity, and decision latency.
- [ ] Separate informational expected derating from warning/critical conditions requiring operator action.
- [ ] Alert on stale/missing telemetry, trust/signature failures, policy invalidity, state-store failures, ownership conflict, scheduler enforcement lag, and component unready state.
- [ ] Detect fleet-wide correlated events separately from isolated node events to avoid alert storms.
- [ ] Use multi-window/burn-rate style alerting for SLO violations where appropriate.
- [ ] Define deduplication/grouping by site/cooling domain/node/reason to keep paging actionable.
- [ ] Attach exact runbook links, owner, severity, and expected first diagnostic action to every page-worthy alert.
- [ ] Provide maintenance/silence controls that cannot disable underlying safety enforcement.
- [ ] Test alerts using synthetic fault scenarios and verify routing/escalation paths.
- [ ] Review thresholds against production baselines and record approved changes.

### B. Architecture, security, resilience, and operability

- [ ] Define an observability schema with stable names, units, labels, cardinality limits, and privacy classification.
- [ ] Expose rate, error, latency, saturation, backlog, resource use, safety-state, and dependency-health signals where applicable.
- [ ] Attach stable node, site, component, policy revision, decision ID, and operation correlation identifiers.
- [ ] Propagate trace context across GAP-09, GAP-10, scheduler, elasticity, policy, and state-store boundaries.
- [ ] Keep unbounded workload IDs, raw payloads, secrets, and high-cardinality data out of default metric labels.
- [ ] Define metric sampling, retention, aggregation, and export intervals appropriate to safety and operational debugging.
- [ ] Distinguish expected thermal derating from sensor trust failure, software failure, attack rejection, and downstream enforcement failure.
- [ ] Provide SLO-oriented dashboards with clearly documented alert thresholds and runbook links.
- [ ] Test that every safety-critical state transition generates the expected metric/log/trace/audit evidence.
- [ ] Verify observability loss cannot alter decision semantics or make the scheduler interpret missing telemetry as healthy capacity.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Dashboards and alerts.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] telemetry schema/data dictionary.
- [ ] dashboard definitions.
- [ ] alert rules plus runbooks.
- [ ] trace/log correlation examples.
- [ ] cardinality/privacy validation report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 25. Retry/backoff/circuit-breaker policy [P2]

**Traceability:** `C025, C053-C056`  
**Audited gap:** bounded dependency behavior for telemetry, state store, policy service, and downstream scheduler calls.  
**Primary checklist profile:** `resilience`

### A. Component-specific engineering requirements

- [ ] Define retry policy independently for GAP-09, policy service, state store, scheduler, elasticity, audit sink, and optional observability backends.
- [ ] Classify operations by idempotency and side-effect safety before enabling automatic retry.
- [ ] Use exponential backoff with jitter, maximum attempts/elapsed time, and a global retry budget to prevent retry storms.
- [ ] Honor deadlines/cancellation from upstream requests and do not continue obsolete work indefinitely.
- [ ] Define circuit-breaker open/half-open/closed thresholds and minimum probe behavior.
- [ ] Ensure breaker-open behavior maps to a conservative ceiling for safety-critical dependencies.
- [ ] Apply queue and concurrency limits so a slow dependency cannot exhaust workers or memory.
- [ ] Expose retries, breaker state, rejected work, timeout rate, and dependency saturation.
- [ ] Test cascading outages and recovery to prove breakers prevent amplification while allowing controlled reconnection.
- [ ] Verify retry configuration itself is policy/config validated and cannot be changed to infinite/unbounded values.

### B. Architecture, security, resilience, and operability

- [ ] Enumerate dependency, process, host, node, network, site, storage, clock, and control-plane failure modes relevant to the component.
- [ ] Define retryable versus terminal errors and prohibit retries for non-idempotent operations unless guarded by idempotency keys or transactions.
- [ ] Use bounded exponential backoff with jitter and explicit retry budgets; never retry indefinitely.
- [ ] Define circuit-breaker thresholds and safe open-state behavior for failing dependencies.
- [ ] Specify degraded operation for each noncritical dependency and fail-closed behavior for safety-critical dependency loss.
- [ ] Bound all queues, buffers, caches, concurrent tasks, and in-flight requests to prevent resource-exhaustion cascades.
- [ ] Specify restart, replay, resume, reconciliation, and duplicate-event semantics.
- [ ] Define recovery time objective and recovery point objective where durable state is involved.
- [ ] Provide automated stall detection and liveness/readiness transitions with hysteresis to avoid flapping.
- [ ] Run deterministic fault-injection experiments and retain machine-readable evidence for each documented failure mode.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Retry/backoff/circuit-breaker policy.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] failure-mode and effects analysis.
- [ ] retry/circuit-breaker specification.
- [ ] fault-injection report.
- [ ] RTO/RPO or recovery objective evidence.
- [ ] degraded-mode runbook.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 26. Partition/reconnect semantics [P2]

**Traceability:** `C018, C055, C057-C058, C089`  
**Audited gap:** specify local authority and reconciliation when edge nodes are disconnected from the control plane.  
**Primary checklist profile:** `resilience`

### A. Component-specific engineering requirements

- [ ] Define which decisions a disconnected edge node may make autonomously and which require central authority.
- [ ] Define validity lifetime for cached policy, calibration, trust roots, ownership leases, and last trusted telemetry during disconnection.
- [ ] Ensure loss of central connectivity cannot implicitly expand local capacity.
- [ ] Define local durable state and monotonic revision rules needed to continue safely offline.
- [ ] Handle local GAP-09 telemetry availability separately from central scheduler/policy reachability.
- [ ] Define how local admissions are journaled for later reconciliation.
- [ ] On reconnect, compare policy revisions, ownership generations, node incarnation, and decision history before resuming central control.
- [ ] Resolve conflicts deterministically with safety constraints taking precedence over utilization optimization.
- [ ] Test long partitions, repeated flap, simultaneous local/central updates, clock drift, stale trust roots, and reconnection storms.
- [ ] Produce a reconnect audit report showing reconciled state and any rejected/stale operations.

### B. Architecture, security, resilience, and operability

- [ ] Enumerate dependency, process, host, node, network, site, storage, clock, and control-plane failure modes relevant to the component.
- [ ] Define retryable versus terminal errors and prohibit retries for non-idempotent operations unless guarded by idempotency keys or transactions.
- [ ] Use bounded exponential backoff with jitter and explicit retry budgets; never retry indefinitely.
- [ ] Define circuit-breaker thresholds and safe open-state behavior for failing dependencies.
- [ ] Specify degraded operation for each noncritical dependency and fail-closed behavior for safety-critical dependency loss.
- [ ] Bound all queues, buffers, caches, concurrent tasks, and in-flight requests to prevent resource-exhaustion cascades.
- [ ] Specify restart, replay, resume, reconciliation, and duplicate-event semantics.
- [ ] Define recovery time objective and recovery point objective where durable state is involved.
- [ ] Provide automated stall detection and liveness/readiness transitions with hysteresis to avoid flapping.
- [ ] Run deterministic fault-injection experiments and retain machine-readable evidence for each documented failure mode.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Partition/reconnect semantics.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] failure-mode and effects analysis.
- [ ] retry/circuit-breaker specification.
- [ ] fault-injection report.
- [ ] RTO/RPO or recovery objective evidence.
- [ ] degraded-mode runbook.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 27. Clock-source/time-service strategy [P2]

**Traceability:** `C048, C051`  
**Audited gap:** authenticated/monotonic freshness handling and documented behavior under clock jumps or time-service loss.  
**Primary checklist profile:** `resilience`

### A. Component-specific engineering requirements

- [ ] Use monotonic time for elapsed-age calculations within a process and authenticated wall-clock only where cross-system timestamps require it.
- [ ] Define acceptable clock skew for telemetry, signatures, policy expiry, ownership leases, and audit timestamps separately.
- [ ] Detect wall-clock jumps forward/backward and prevent them from making stale evidence appear fresh.
- [ ] Define behavior when NTP/PTP/time-attestation is unavailable or loses trust.
- [ ] Carry both source observed-at and local receive-at timestamps when evaluating cross-node freshness.
- [ ] Prevent replay acceptance after restart by persisting monotonic source sequence/revision state where available.
- [ ] Expose clock source, sync status, estimated offset/error, and last trusted sync in health output.
- [ ] Alert when time uncertainty exceeds the safety envelope even if the process remains otherwise healthy.
- [ ] Test leap/step adjustments, VM suspend/resume, DST-independent UTC behavior, extreme skew, and service loss.
- [ ] Document every algorithm that depends on time and which clock it uses.

### B. Architecture, security, resilience, and operability

- [ ] Enumerate dependency, process, host, node, network, site, storage, clock, and control-plane failure modes relevant to the component.
- [ ] Define retryable versus terminal errors and prohibit retries for non-idempotent operations unless guarded by idempotency keys or transactions.
- [ ] Use bounded exponential backoff with jitter and explicit retry budgets; never retry indefinitely.
- [ ] Define circuit-breaker thresholds and safe open-state behavior for failing dependencies.
- [ ] Specify degraded operation for each noncritical dependency and fail-closed behavior for safety-critical dependency loss.
- [ ] Bound all queues, buffers, caches, concurrent tasks, and in-flight requests to prevent resource-exhaustion cascades.
- [ ] Specify restart, replay, resume, reconciliation, and duplicate-event semantics.
- [ ] Define recovery time objective and recovery point objective where durable state is involved.
- [ ] Provide automated stall detection and liveness/readiness transitions with hysteresis to avoid flapping.
- [ ] Run deterministic fault-injection experiments and retain machine-readable evidence for each documented failure mode.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Clock-source/time-service strategy.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] failure-mode and effects analysis.
- [ ] retry/circuit-breaker specification.
- [ ] fault-injection report.
- [ ] RTO/RPO or recovery objective evidence.
- [ ] degraded-mode runbook.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 28. Secret/key isolation model [P2]

**Traceability:** `C039, C042-C047`  
**Audited gap:** capability-scoped identities, no ambient secret access, managed key rotation, and encrypted transport/state where sensitive metadata is present.  
**Primary checklist profile:** `security`

### A. Component-specific engineering requirements

- [ ] Issue separate workload/service identities for telemetry read, policy read, state write, scheduler publish, audit write, and observability export capabilities.
- [ ] Deny generic ambient credentials that grant unrelated storage/network/control-plane privileges.
- [ ] Use short-lived credentials or managed identity where supported, with automated rotation and revocation.
- [ ] Protect signing keys/trust roots in dedicated key-management/HSM-backed systems where appropriate.
- [ ] Encrypt network traffic to GAP-09, GAP-11, policy, state, scheduler, elasticity, and audit services.
- [ ] Encrypt sensitive local persisted state or diagnostic bundles when they contain topology/security metadata.
- [ ] Define secret bootstrap without embedding credentials in the artifact, source tree, ordinary environment dump, or logs.
- [ ] Create explicit egress/ingress allowlists for the GAP-10 service identity.
- [ ] Test credential expiry, rotation, revocation, wrong audience, privilege escalation attempts, and secret-scraping diagnostics.
- [ ] Continuously inventory granted permissions and alert on privilege drift from the approved capability model.

### B. Architecture, security, resilience, and operability

- [ ] Define assets, trust boundaries, identities, attacker capabilities, abuse cases, and security invariants in the GAP-10 threat model.
- [ ] Use workload- or service-scoped identity with least privilege and deny ambient filesystem, network, device, and secret authority.
- [ ] Authenticate every control-plane peer before accepting safety-relevant data or commands.
- [ ] Authorize every privileged operation against explicit capabilities or roles; authentication alone is insufficient.
- [ ] Use modern authenticated transport and managed key rotation; reject insecure downgrade paths.
- [ ] Define revocation behavior and maximum exposure window for compromised credentials or signing keys.
- [ ] Protect against replay with bounded freshness, nonce/sequence/revision checks, and monotonic state where applicable.
- [ ] Keep raw secrets out of logs, metrics, traces, crash dumps, diagnostic bundles, and normal configuration files.
- [ ] Emit tamper-evident audit records for authentication failures, authorization denials, trust changes, and administrative actions.
- [ ] Run adversarial tests for spoofing, replay, privilege escalation, parser abuse, resource exhaustion, and malicious downgrade attempts.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Secret/key isolation model.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] threat-model update.
- [ ] identity/capability matrix.
- [ ] key/secret lifecycle runbook.
- [ ] adversarial test report.
- [ ] tamper-evident audit evidence.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 29. End-to-end integration test harness [P3]

**Traceability:** `C030, C083`  
**Audited gap:** real GAP-09 -> GAP-10 -> scheduler/elasticity test path with success, stale, forged, emergency, and recovery scenarios.  
**Primary checklist profile:** `validation`

### A. Component-specific engineering requirements

- [ ] Construct a real or protocol-faithful path from GAP-09 telemetry through GAP-10 decision/state to scheduler and elasticity enforcement.
- [ ] Use the same schemas, authentication modes, retry policies, and version negotiation as production rather than test-only shortcuts.
- [ ] Cover nominal, elevated, critical, emergency, recovery, stale, future, replayed, malformed, and forged telemetry.
- [ ] Cover power-only, battery-only, temperature-only, combined-constraint, and shared-domain constraint cases.
- [ ] Assert both GAP-10 output and the final applied scheduler/elasticity capacity.
- [ ] Inject downstream rejection/timeouts and verify GAP-10 health/explain/alerts show enforcement mismatch.
- [ ] Exercise policy activation/rollback and controller failover while decisions are in flight.
- [ ] Capture end-to-end decision latency and propagation/enforcement lag.
- [ ] Run at least one supported cross-version compatibility combination in CI.
- [ ] Publish machine-readable evidence linking scenarios to C030/C083 and build/policy versions.

### B. Architecture, security, resilience, and operability

- [ ] Define a hermetic test topology and deterministic fixture set with pinned dependency versions.
- [ ] Cover nominal, boundary, invalid, stale, replayed, degraded, emergency, recovery, and rollback scenarios.
- [ ] Ensure failures are asserted using machine-readable outputs rather than brittle log-string matching.
- [ ] Use seeded randomness where fuzzing or randomized scheduling is employed so failures can be reproduced.
- [ ] Capture code version, policy revision, schema versions, test seed, environment, and hardware class in results.
- [ ] Separate unit, contract, integration, concurrency, fault-injection, performance, and certification suites.
- [ ] Fail CI on skipped mandatory safety tests unless an explicit, approved waiver is attached.
- [ ] Retain artifacts such as traces, input fixtures, output decisions, metrics, and crash data for failed runs.
- [ ] Define pass/fail thresholds before execution and block releases on regression beyond approved budgets.
- [ ] Emit a machine-readable acceptance report that links every result to requirement and build provenance.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to End-to-end integration test harness.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] test plan and coverage matrix.
- [ ] deterministic fixtures/seeds.
- [ ] machine-readable test results.
- [ ] failure artifacts/minimized regressions.
- [ ] requirements traceability report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 30. Contract/schema validator tests [P3]

**Traceability:** `C082, C085`  
**Audited gap:** validate JSON instances against the bundled schemas and fuzz untrusted telemetry/policy boundaries.  
**Primary checklist profile:** `validation`

### A. Component-specific engineering requirements

- [ ] Validate every bundled positive fixture against its declared Draft 2020-12 schema in CI.
- [ ] Create negative fixtures for missing required fields, wrong types, extra forbidden fields, out-of-range values, NaN/Infinity encodings, and invalid enums.
- [ ] Add property/fuzz generation for temperatures, power values, timestamps, IDs, policy thresholds, and nested payload sizes.
- [ ] Limit parser depth, string length, array cardinality, numeric magnitude, and total message size.
- [ ] Test unknown minor fields/version evolution according to the declared compatibility policy.
- [ ] Test canonicalization/signature behavior so semantically altered policy cannot verify against a signed digest.
- [ ] Fuzz timestamp parsing, Unicode identifiers, duplicate JSON keys if the parser permits them, and malformed encodings.
- [ ] Run sanitizers/runtime hardening tools appropriate to any non-Python boundary libraries used later.
- [ ] Retain minimized crashing/rejected corpus inputs as regression fixtures.
- [ ] Block release on schema drift where code accepts data the published schema rejects or vice versa.

### B. Architecture, security, resilience, and operability

- [ ] Define a hermetic test topology and deterministic fixture set with pinned dependency versions.
- [ ] Cover nominal, boundary, invalid, stale, replayed, degraded, emergency, recovery, and rollback scenarios.
- [ ] Ensure failures are asserted using machine-readable outputs rather than brittle log-string matching.
- [ ] Use seeded randomness where fuzzing or randomized scheduling is employed so failures can be reproduced.
- [ ] Capture code version, policy revision, schema versions, test seed, environment, and hardware class in results.
- [ ] Separate unit, contract, integration, concurrency, fault-injection, performance, and certification suites.
- [ ] Fail CI on skipped mandatory safety tests unless an explicit, approved waiver is attached.
- [ ] Retain artifacts such as traces, input fixtures, output decisions, metrics, and crash data for failed runs.
- [ ] Define pass/fail thresholds before execution and block releases on regression beyond approved budgets.
- [ ] Emit a machine-readable acceptance report that links every result to requirement and build provenance.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Contract/schema validator tests.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] test plan and coverage matrix.
- [ ] deterministic fixtures/seeds.
- [ ] machine-readable test results.
- [ ] failure artifacts/minimized regressions.
- [ ] requirements traceability report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 31. Concurrency/race test suite [P3]

**Traceability:** `C086`  
**Audited gap:** simultaneous updates, policy swaps, controller failover, duplicate samples, and node deletion/recreation.  
**Primary checklist profile:** `validation`

### A. Component-specific engineering requirements

- [ ] Exercise concurrent telemetry updates for the same node and prove deterministic last-valid-sample/replay semantics.
- [ ] Race policy revision activation against telemetry update and ensure one complete policy revision is used per decision.
- [ ] Race state persistence against process shutdown/restart and verify crash-consistent recovery.
- [ ] Race leader failover/publication and verify downstream fencing rejects stale owners.
- [ ] Race duplicate scheduler publications and prove idempotent applied capacity.
- [ ] Race node deletion/recreation using the same display name and ensure old state cannot attach to the new node incarnation.
- [ ] Exercise thousands of nodes updating concurrently to reveal lock contention and shared-state corruption.
- [ ] Use deterministic schedulers/model-checking or repeated seeded stress where practical.
- [ ] Instrument lock wait, queue depth, transaction conflicts, CAS retries, and ownership conflicts.
- [ ] Retain exact seed/interleaving evidence for every discovered race regression.

### B. Architecture, security, resilience, and operability

- [ ] Define a hermetic test topology and deterministic fixture set with pinned dependency versions.
- [ ] Cover nominal, boundary, invalid, stale, replayed, degraded, emergency, recovery, and rollback scenarios.
- [ ] Ensure failures are asserted using machine-readable outputs rather than brittle log-string matching.
- [ ] Use seeded randomness where fuzzing or randomized scheduling is employed so failures can be reproduced.
- [ ] Capture code version, policy revision, schema versions, test seed, environment, and hardware class in results.
- [ ] Separate unit, contract, integration, concurrency, fault-injection, performance, and certification suites.
- [ ] Fail CI on skipped mandatory safety tests unless an explicit, approved waiver is attached.
- [ ] Retain artifacts such as traces, input fixtures, output decisions, metrics, and crash data for failed runs.
- [ ] Define pass/fail thresholds before execution and block releases on regression beyond approved budgets.
- [ ] Emit a machine-readable acceptance report that links every result to requirement and build provenance.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Concurrency/race test suite.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] test plan and coverage matrix.
- [ ] deterministic fixtures/seeds.
- [ ] machine-readable test results.
- [ ] failure artifacts/minimized regressions.
- [ ] requirements traceability report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 32. Fault-injection suite [P3]

**Traceability:** `C060, C089`  
**Audited gap:** sensor dropout, stuck-high/stuck-low values, telemetry delay, store outage, scheduler outage, partition, process crash, and restart.  
**Primary checklist profile:** `validation`

### A. Component-specific engineering requirements

- [ ] Inject complete and partial loss of each sensor stream, including stuck-high, stuck-low, frozen timestamp, noisy, and implausible values.
- [ ] Inject telemetry transport delay, reordering, duplication, corruption, authentication failure, and key rotation mid-stream.
- [ ] Inject state-store unavailability, latency, partial write, stale replica, corruption, and recovery.
- [ ] Inject policy service outage, invalid revision, failed signature verification, rollback, and mixed-version response.
- [ ] Inject scheduler/elasticity timeout, rejection, partial acknowledgement, and stale enforcement state.
- [ ] Inject controller process kill, host reboot, lease loss, split-brain conditions, and rapid failover.
- [ ] Inject network partitions between edge/site/control-plane components and test reconnect reconciliation.
- [ ] Inject clock jump/time-service loss and validate freshness/lease behavior.
- [ ] Assert safety invariants continuously during faults, not only final recovery state.
- [ ] Compare measured detection/recovery time to documented objectives and retain automated evidence.

### B. Architecture, security, resilience, and operability

- [ ] Define a hermetic test topology and deterministic fixture set with pinned dependency versions.
- [ ] Cover nominal, boundary, invalid, stale, replayed, degraded, emergency, recovery, and rollback scenarios.
- [ ] Ensure failures are asserted using machine-readable outputs rather than brittle log-string matching.
- [ ] Use seeded randomness where fuzzing or randomized scheduling is employed so failures can be reproduced.
- [ ] Capture code version, policy revision, schema versions, test seed, environment, and hardware class in results.
- [ ] Separate unit, contract, integration, concurrency, fault-injection, performance, and certification suites.
- [ ] Fail CI on skipped mandatory safety tests unless an explicit, approved waiver is attached.
- [ ] Retain artifacts such as traces, input fixtures, output decisions, metrics, and crash data for failed runs.
- [ ] Define pass/fail thresholds before execution and block releases on regression beyond approved budgets.
- [ ] Emit a machine-readable acceptance report that links every result to requirement and build provenance.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Fault-injection suite.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] test plan and coverage matrix.
- [ ] deterministic fixtures/seeds.
- [ ] machine-readable test results.
- [ ] failure artifacts/minimized regressions.
- [ ] requirements traceability report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 33. Benchmark/soak/fleet-scale harness [P3]

**Traceability:** `C061-C070, C088`  
**Audited gap:** p50/p95/p99 decision latency, memory growth, CPU cost, queue saturation, and long-running stability across realistic fleet sizes.  
**Primary checklist profile:** `performance`

### A. Component-specific engineering requirements

- [ ] Define representative fleet tiers such as 1, 100, 1k, 10k, and target maximum nodes with realistic sensor rates.
- [ ] Benchmark decision path latency independent of downstream network latency and also end-to-end applied-ceiling latency.
- [ ] Measure p50/p95/p99/max for telemetry ingest, decision compute, state persistence, policy lookup, publish, and acknowledgement.
- [ ] Measure CPU, RSS, allocation rate, garbage collection, file descriptors, threads/tasks, and network/storage throughput.
- [ ] Run sustained soak long enough to reveal memory/handle leaks, state growth, metric-cardinality growth, and timer drift.
- [ ] Run burst scenarios representing site power/cooling events where many nodes change band simultaneously.
- [ ] Run overload until admission/backpressure activates and verify graceful degradation without unsafe stale capacity.
- [ ] Measure startup/restart recovery time at realistic state volumes.
- [ ] Quantify GAP-10 controller power/CPU overhead on constrained edge hardware.
- [ ] Publish release-blocking regression thresholds and compare every candidate build to a pinned baseline.

### B. Architecture, security, resilience, and operability

- [ ] Define reproducible workload models, fleet sizes, sensor rates, decision rates, and hardware profiles.
- [ ] Measure p50, p95, p99, maximum, and timeout-rate latency rather than averages alone.
- [ ] Measure CPU, memory, allocation rate, queue depth, storage I/O, network I/O, and power overhead.
- [ ] Benchmark startup, steady state, burst, overload, scale-out, scale-in, reconnect, and recovery.
- [ ] Detect memory leaks, unbounded cache growth, descriptor leaks, task leaks, and queue accumulation during soak tests.
- [ ] Set explicit saturation signals and hard resource limits that trigger safe load shedding before process failure.
- [ ] Compare optimized and reference paths against golden semantic outputs to ensure optimization never changes safety behavior.
- [ ] Define hardware-normalized baselines so regressions can be compared across CPU architectures and node classes.
- [ ] Publish benchmark methodology and raw result artifacts with build and environment provenance.
- [ ] Block release when approved startup, density, throughput, resource, power, or tail-latency budgets regress.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Benchmark/soak/fleet-scale harness.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] benchmark methodology.
- [ ] raw benchmark results.
- [ ] baseline and regression thresholds.
- [ ] soak/leak report.
- [ ] capacity/saturation model.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 34. Cross-platform/hardware compatibility matrix [P3]

**Traceability:** `C084, C093`  
**Audited gap:** supported CPU architectures, sensor providers, operating systems/runtimes, GAP-09/GAP-11 schema versions, and scheduler versions.  
**Primary checklist profile:** `validation`

### A. Component-specific engineering requirements

- [ ] List supported CPU architectures, OS/runtime versions, Python/runtime versions, hypervisors/container modes, and edge hardware classes.
- [ ] List supported sensor providers/drivers and the exact telemetry capabilities required from each.
- [ ] List supported GAP-09/GAP-11 schema versions plus scheduler/elasticity/state-store/policy-service versions.
- [ ] Define minimum firmware/BIOS/BMC/driver versions when sensor correctness depends on them.
- [ ] Automate at least smoke/contract tests for every supported matrix row and deeper tests for tier-1 combinations.
- [ ] Mark unsupported/experimental combinations explicitly and prevent silent production enablement.
- [ ] Test endian/word-size/numeric precision differences where relevant across architectures.
- [ ] Test suspend/resume, virtualization clock behavior, and device hot-plug on platforms that support them.
- [ ] Publish deprecation dates and migration guidance before dropping a supported combination.
- [ ] Bind each release acceptance report to the exact compatibility matrix revision used for certification.

### B. Architecture, security, resilience, and operability

- [ ] Define a hermetic test topology and deterministic fixture set with pinned dependency versions.
- [ ] Cover nominal, boundary, invalid, stale, replayed, degraded, emergency, recovery, and rollback scenarios.
- [ ] Ensure failures are asserted using machine-readable outputs rather than brittle log-string matching.
- [ ] Use seeded randomness where fuzzing or randomized scheduling is employed so failures can be reproduced.
- [ ] Capture code version, policy revision, schema versions, test seed, environment, and hardware class in results.
- [ ] Separate unit, contract, integration, concurrency, fault-injection, performance, and certification suites.
- [ ] Fail CI on skipped mandatory safety tests unless an explicit, approved waiver is attached.
- [ ] Retain artifacts such as traces, input fixtures, output decisions, metrics, and crash data for failed runs.
- [ ] Define pass/fail thresholds before execution and block releases on regression beyond approved budgets.
- [ ] Emit a machine-readable acceptance report that links every result to requirement and build provenance.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Cross-platform/hardware compatibility matrix.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] test plan and coverage matrix.
- [ ] deterministic fixtures/seeds.
- [ ] machine-readable test results.
- [ ] failure artifacts/minimized regressions.
- [ ] requirements traceability report.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 35. SBOM, dependency pinning, and vulnerability policy [P3]

**Traceability:** `C031, C045, C094`  
**Audited gap:** machine-readable dependency inventory, approved versions, CVE response SLA, and end-of-life policy.  
**Primary checklist profile:** `release`

### A. Component-specific engineering requirements

- [ ] Generate CycloneDX/SPDX or equivalent SBOM covering direct, transitive, build, and runtime dependencies.
- [ ] Pin dependency versions/hashes and prohibit unconstrained floating production dependencies.
- [ ] Record license, source, maintainer, support status, and end-of-life date where known.
- [ ] Define approved vulnerability sources and automated scanning cadence.
- [ ] Classify vulnerability response SLA by exploitability/severity and whether the dependency is reachable in GAP-10.
- [ ] Define emergency patch path that preserves signing, testing, rollback, and audit requirements.
- [ ] Prohibit unsupported/EOL dependencies in release builds absent an approved expiring waiver.
- [ ] Verify dependency integrity and provenance before build use.
- [ ] Continuously compare deployed dependency inventory with the release SBOM to detect drift.
- [ ] Include SBOM/scanner results in machine-readable production-gate evidence.

### B. Architecture, security, resilience, and operability

- [ ] Define immutable build inputs and pin toolchain, dependency, schema, and packaging versions.
- [ ] Generate an SBOM and dependency/license inventory for every release artifact.
- [ ] Generate checksums, signatures, build provenance, and reproducibility metadata.
- [ ] Verify release artifacts in a clean environment before promotion.
- [ ] Define compatibility gates against supported GAP-09, GAP-11, scheduler, elasticity, state-store, and runtime versions.
- [ ] Use staged promotion with canary cohorts selected by site and hardware class.
- [ ] Define automated rollback triggers using safety, error, latency, and enforcement-health signals.
- [ ] Preserve previous known-good artifacts and policy revisions for bounded rollback.
- [ ] Publish machine-readable acceptance evidence and human-readable release notes.
- [ ] Require explicit production approval after all mandatory architecture, security, resilience, performance, observability, and operations gates pass.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to SBOM, dependency pinning, and vulnerability policy.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] SBOM/provenance/signature bundle.
- [ ] reproducible build report.
- [ ] compatibility evidence.
- [ ] rollout/rollback evidence.
- [ ] signed release acceptance record.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 36. Artifact signing/provenance and reproducible release build [P3]

**Traceability:** `C045, C090, C100`  
**Audited gap:** signed package, build attestation, digest manifest, and machine-readable acceptance evidence.  
**Primary checklist profile:** `release`

### A. Component-specific engineering requirements

- [ ] Build from declared source revision and pinned toolchain in a clean, isolated environment.
- [ ] Generate a deterministic manifest of every packaged file and SHA-256 or stronger digest.
- [ ] Sign the release artifact and manifest with an approved release identity/key.
- [ ] Produce SLSA-style or equivalent build provenance identifying source, builder, inputs, invocation, and output digests.
- [ ] Eliminate nondeterministic timestamps/order/metadata where feasible and document remaining reproducibility limits.
- [ ] Rebuild independently and compare artifact digests or normalized content according to the reproducibility target.
- [ ] Verify signatures/provenance before deployment and fail closed on mismatch or unknown signer.
- [ ] Bind schemas, fixtures, policy defaults, checklist/evidence, changelog, and VERSION to the same release revision.
- [ ] Archive source, build recipe, SBOM, test evidence, signatures, and provenance for later incident reconstruction.
- [ ] Block promotion unless artifact verification succeeds in the target deployment environment.

### B. Architecture, security, resilience, and operability

- [ ] Define immutable build inputs and pin toolchain, dependency, schema, and packaging versions.
- [ ] Generate an SBOM and dependency/license inventory for every release artifact.
- [ ] Generate checksums, signatures, build provenance, and reproducibility metadata.
- [ ] Verify release artifacts in a clean environment before promotion.
- [ ] Define compatibility gates against supported GAP-09, GAP-11, scheduler, elasticity, state-store, and runtime versions.
- [ ] Use staged promotion with canary cohorts selected by site and hardware class.
- [ ] Define automated rollback triggers using safety, error, latency, and enforcement-health signals.
- [ ] Preserve previous known-good artifacts and policy revisions for bounded rollback.
- [ ] Publish machine-readable acceptance evidence and human-readable release notes.
- [ ] Require explicit production approval after all mandatory architecture, security, resilience, performance, observability, and operations gates pass.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Artifact signing/provenance and reproducible release build.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] SBOM/provenance/signature bundle.
- [ ] reproducible build report.
- [ ] compatibility evidence.
- [ ] rollout/rollback evidence.
- [ ] signed release acceptance record.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 37. Canary/staged rollout controller [P3]

**Traceability:** `C092`  
**Audited gap:** policy/code rollout by site and hardware cohort with automated rollback triggers.  
**Primary checklist profile:** `release`

### A. Component-specific engineering requirements

- [ ] Define rollout cohorts by site, hardware class, sensor provider, battery/cooling class, and criticality to avoid correlated unknowns.
- [ ] Separate code rollout from policy/calibration rollout while supporting coordinated compatibility gates.
- [ ] Define pre-canary, canary, staged, broad, and complete phases with explicit entry/exit criteria.
- [ ] Monitor safety-state distribution, excluded capacity, telemetry rejection, enforcement lag, errors, latency, and resource use per cohort.
- [ ] Use automated rollback triggers for statistically/materially significant regressions and hard safety invariant violations.
- [ ] Ensure rollback restores a known-good artifact plus compatible policy/schema/state migration path.
- [ ] Pause rollout on observability blindness or inability to verify applied ceilings.
- [ ] Prevent automatic forward rollout from overriding a manually declared incident freeze.
- [ ] Test rollout interruption, controller restart, failed cohort, rollback, and resumed deployment in staging.
- [ ] Produce signed rollout evidence showing cohort membership, versions, metrics, decisions, and final disposition.

### B. Architecture, security, resilience, and operability

- [ ] Define immutable build inputs and pin toolchain, dependency, schema, and packaging versions.
- [ ] Generate an SBOM and dependency/license inventory for every release artifact.
- [ ] Generate checksums, signatures, build provenance, and reproducibility metadata.
- [ ] Verify release artifacts in a clean environment before promotion.
- [ ] Define compatibility gates against supported GAP-09, GAP-11, scheduler, elasticity, state-store, and runtime versions.
- [ ] Use staged promotion with canary cohorts selected by site and hardware class.
- [ ] Define automated rollback triggers using safety, error, latency, and enforcement-health signals.
- [ ] Preserve previous known-good artifacts and policy revisions for bounded rollback.
- [ ] Publish machine-readable acceptance evidence and human-readable release notes.
- [ ] Require explicit production approval after all mandatory architecture, security, resilience, performance, observability, and operations gates pass.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Canary/staged rollout controller.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] SBOM/provenance/signature bundle.
- [ ] reproducible build report.
- [ ] compatibility evidence.
- [ ] rollout/rollback evidence.
- [ ] signed release acceptance record.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 38. Backup/restore/reconstruction runbook [P3]

**Traceability:** `C095-C097`  
**Audited gap:** restore policy/state, recover ownership safely, and verify downstream ceilings before reopening placement.  
**Primary checklist profile:** `resilience`

### A. Component-specific engineering requirements

- [ ] Define which GAP-10 data must be backed up versus reconstructed from authoritative sources.
- [ ] Back up policy metadata, calibration references, ownership/state metadata, audit pointers, and durable node state required for safe recovery.
- [ ] Encrypt and integrity-protect backups with separate restore authorization.
- [ ] Define RPO/RTO and backup frequency based on the safety impact of lost state.
- [ ] Test restore into a clean environment and validate schema/version compatibility before activation.
- [ ] On restore, preserve replay protection and ownership generations so old data cannot resurrect stale authority.
- [ ] Reconcile restored GAP-10 state with live GAP-09 telemetry and downstream applied scheduler ceilings before reopening placement.
- [ ] Define site-disaster recovery where the original state store/coordination service is lost.
- [ ] Provide reconstruction mode that starts conservatively when durable data is unavailable rather than fabricating nominal state.
- [ ] Run periodic restore drills and retain evidence that final applied ceilings were verified before service reopening.

### B. Architecture, security, resilience, and operability

- [ ] Enumerate dependency, process, host, node, network, site, storage, clock, and control-plane failure modes relevant to the component.
- [ ] Define retryable versus terminal errors and prohibit retries for non-idempotent operations unless guarded by idempotency keys or transactions.
- [ ] Use bounded exponential backoff with jitter and explicit retry budgets; never retry indefinitely.
- [ ] Define circuit-breaker thresholds and safe open-state behavior for failing dependencies.
- [ ] Specify degraded operation for each noncritical dependency and fail-closed behavior for safety-critical dependency loss.
- [ ] Bound all queues, buffers, caches, concurrent tasks, and in-flight requests to prevent resource-exhaustion cascades.
- [ ] Specify restart, replay, resume, reconciliation, and duplicate-event semantics.
- [ ] Define recovery time objective and recovery point objective where durable state is involved.
- [ ] Provide automated stall detection and liveness/readiness transitions with hysteresis to avoid flapping.
- [ ] Run deterministic fault-injection experiments and retain machine-readable evidence for each documented failure mode.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Backup/restore/reconstruction runbook.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] failure-mode and effects analysis.
- [ ] retry/circuit-breaker specification.
- [ ] fault-injection report.
- [ ] RTO/RPO or recovery objective evidence.
- [ ] degraded-mode runbook.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 39. Incident severity/paging/escalation definitions [P3]

**Traceability:** `C009, C097`  
**Audited gap:** named accountable owner, escalation path, thermal-safety incident classes, and response objectives.  
**Primary checklist profile:** `governance`

### A. Component-specific engineering requirements

- [ ] Define incident classes for thermal emergency, fleet-wide cooling/power event, stale telemetry, trust/signature attack, policy failure, split-brain, state-store failure, and enforcement mismatch.
- [ ] Assign severity based on safety impact, affected capacity/sites, duration, and ability to enforce ceilings—not merely service uptime.
- [ ] Define paging targets, acknowledgement objectives, escalation timers, and executive/site escalation where applicable.
- [ ] Assign primary/secondary owning teams for GAP-10, GAP-09, scheduler, facility/cooling, security, and platform dependencies.
- [ ] Provide first-response runbooks with safe containment actions that do not expand capacity accidentally.
- [ ] Define evidence preservation requirements for audit events, decisions, telemetry, policy, state, traces, and deployed artifact versions.
- [ ] Create communication templates/status fields for impacted sites and operational stakeholders.
- [ ] Define recovery criteria including verified downstream ceiling convergence, not just GAP-10 process recovery.
- [ ] Require post-incident root-cause review and track corrective actions to closure.
- [ ] Exercise at least one tabletop/game-day scenario for each highest-severity incident class.

### B. Architecture, security, resilience, and operability

- [ ] Assign a named accountable owner plus backup/on-call ownership for the capability.
- [ ] Record the architectural decision, alternatives considered, safety rationale, and rejected alternatives.
- [ ] Maintain a requirements-to-design-to-code-to-test traceability chain.
- [ ] Track exceptions and waivers with owner, justification, compensating control, expiry, and re-review date.
- [ ] Define service SLOs, error budgets, escalation objectives, and support commitments.
- [ ] Schedule periodic access, policy, dependency, configuration, and architecture reviews.
- [ ] Require change management for safety-critical defaults, thresholds, trust roots, and enforcement semantics.
- [ ] Define deprecation and end-of-life policy for schemas, APIs, artifacts, and dependency versions.
- [ ] Retain audit evidence according to documented retention and access-control policy.
- [ ] Require formal production exit approval and prohibit implicit certification based solely on checklist completion claims.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Incident severity/paging/escalation definitions.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] approved ADR.
- [ ] owner/escalation record.
- [ ] exception/waiver register.
- [ ] review minutes/evidence.
- [ ] signed production exit gate.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## 40. Architecture decision record and exception register [P3]

**Traceability:** `C010, C098-C100`  
**Audited gap:** approved ADR, waivers with owners/expiry, recurring architecture review, and formal production exit gate.  
**Primary checklist profile:** `governance`

### A. Component-specific engineering requirements

- [ ] Create an ADR describing GAP-10 responsibility, trust boundaries, data/control flows, state model, enforcement path, and key technology choices.
- [ ] Document rejected alternatives and safety/performance trade-offs, including why fail-closed and most-restrictive-wins semantics are required.
- [ ] Link the ADR to canonical contracts, schemas, policy model, state model, threat model, SLOs, and production topology.
- [ ] Create a machine-readable/human-readable exception register with unique ID, affected requirement, owner, rationale, compensating control, risk, approval, and expiry.
- [ ] Prohibit permanent waivers; require expiry and explicit re-review.
- [ ] Flag exceptions that can increase schedulable capacity as high-risk and require architecture/security/safety approval.
- [ ] Review ADR and active exceptions on a defined cadence and upon material dependency/topology/security changes.
- [ ] Create a production exit checklist covering C001–C100 with evidence links rather than self-attested completion text.
- [ ] Require open P0/P1 gaps and expired high-risk exceptions to block production certification.
- [ ] Sign/date the production decision and retain immutable evidence tying approval to an exact build, policy set, compatibility matrix, and test report.

### B. Architecture, security, resilience, and operability

- [ ] Assign a named accountable owner plus backup/on-call ownership for the capability.
- [ ] Record the architectural decision, alternatives considered, safety rationale, and rejected alternatives.
- [ ] Maintain a requirements-to-design-to-code-to-test traceability chain.
- [ ] Track exceptions and waivers with owner, justification, compensating control, expiry, and re-review date.
- [ ] Define service SLOs, error budgets, escalation objectives, and support commitments.
- [ ] Schedule periodic access, policy, dependency, configuration, and architecture reviews.
- [ ] Require change management for safety-critical defaults, thresholds, trust roots, and enforcement semantics.
- [ ] Define deprecation and end-of-life policy for schemas, APIs, artifacts, and dependency versions.
- [ ] Retain audit evidence according to documented retention and access-control policy.
- [ ] Require formal production exit approval and prohibit implicit certification based solely on checklist completion claims.
- [ ] Define a single accountable engineering owner and an operational/on-call owner for this component.
- [ ] Write a short design/ADR section defining scope, non-goals, authoritative data, trust boundaries, and upstream/downstream dependencies.
- [ ] Define versioned typed interfaces and reject unsupported major versions deterministically.
- [ ] Use declarative configuration with schema validation, secure defaults, documented units, and explicit bounds.
- [ ] Define a fail-closed default for missing, invalid, stale, unauthorized, conflicting, or unavailable safety-critical evidence.
- [ ] Apply least privilege and document the exact identities/capabilities/permissions required.
- [ ] Define timeout, cancellation, retry, idempotency, backpressure, and resource-limit semantics for external interactions.
- [ ] Emit structured reason/error codes and correlation identifiers suitable for automation and incident analysis.
- [ ] Expose health/readiness plus metrics, logs, traces, and audit events needed to verify correct operation.
- [ ] Define deterministic restart/recovery behavior and ensure process restart cannot silently relax a previously justified restriction.
- [ ] Create unit/contract tests for all boundary values and invalid input classes.
- [ ] Create integration/fault/concurrency tests covering the component’s interactions with adjacent GAP-10 services.
- [ ] Define performance/resource budgets and prove queue, memory, concurrency, and latency remain bounded at target fleet scale.
- [ ] Provide deployment, rollback, emergency-disable, and operator troubleshooting procedures.
- [ ] Attach machine-readable acceptance evidence to the release and map it to the cited GAP-10 checklist requirements.

### C. Verification and acceptance gate

- [ ] Demonstrate the component in a production-faithful environment using the active GAP-10 schemas/contracts and a pinned build.
- [ ] Prove nominal, boundary, degraded, failure, emergency, recovery, restart, and rollback behavior relevant to Architecture decision record and exception register.
- [ ] Prove negative cases fail with stable machine-readable reason/error codes and do not silently fall back to unconstrained capacity.
- [ ] Verify security controls with unauthorized, unauthenticated, replayed, stale, malformed, and resource-exhaustion scenarios where applicable.
- [ ] Verify the downstream applied state matches the GAP-10 desired state and alarm on any enforcement divergence.
- [ ] Measure and record latency/resource overhead against approved budgets at representative scale.
- [ ] Complete a reviewer sign-off that the evidence satisfies the cited GAP-10 requirements and contains no unapproved skipped mandatory tests.

**Required closure artifacts:**

- [ ] approved ADR.
- [ ] owner/escalation record.
- [ ] exception/waiver register.
- [ ] review minutes/evidence.
- [ ] signed production exit gate.
- [ ] Requirement-to-evidence links recorded in the GAP-10 production traceability matrix.
- [ ] No unresolved blocker or expired waiver remains for this component.

## Priority closure gates

### P0 — Production-enforcement gate

- [ ] Component 01: Authenticated telemetry adapter for GAP-09 is implemented, verified, operationally owned, and evidenced.
- [ ] Component 02: Downstream scheduler enforcement adapter is implemented, verified, operationally owned, and evidenced.
- [ ] Component 03: Elasticity-plane enforcement adapter is implemented, verified, operationally owned, and evidenced.
- [ ] Component 04: Durable per-node state store is implemented, verified, operationally owned, and evidenced.
- [ ] Component 05: Atomic policy distribution and activation service is implemented, verified, operationally owned, and evidenced.
- [ ] Component 06: Policy authorization/signature verification is implemented, verified, operationally owned, and evidenced.
- [ ] Component 07: Explicit fail-closed scheduler behavior when GAP-10 is absent/unhealthy is implemented, verified, operationally owned, and evidenced.
- [ ] Component 08: Controller ownership/leader fencing is implemented, verified, operationally owned, and evidenced.
- [ ] End-to-end fail-closed proof demonstrates GAP-09 → GAP-10 → scheduler/elasticity cannot accidentally reopen capacity during dependency, restart, policy, state, or ownership failures.

### P1 — Core operational-readiness gate

- [ ] Component 09: Hardware/site calibration inventory is implemented, verified, operationally owned, and evidenced.
- [ ] Component 10: Multi-sensor aggregation model is implemented, verified, operationally owned, and evidenced.
- [ ] Component 11: Thermal rate-of-rise predictor is implemented, verified, operationally owned, and evidenced.
- [ ] Component 12: Battery discharge/remaining-runtime estimator is implemented, verified, operationally owned, and evidenced.
- [ ] Component 13: Cooling-domain/site correlation is implemented, verified, operationally owned, and evidenced.
- [ ] Component 14: Accelerator thermal integration with GAP-11 is implemented, verified, operationally owned, and evidenced.
- [ ] Component 15: Workload-class-aware shedding policy is implemented, verified, operationally owned, and evidenced.
- [ ] Component 16: Constraint-precedence engine is implemented, verified, operationally owned, and evidenced.
- [ ] Component 17: Health/readiness API is implemented, verified, operationally owned, and evidenced.
- [ ] Component 18: Quarantine/freeze/emergency-disable control is implemented, verified, operationally owned, and evidenced.
- [ ] Hardware/calibration, predictive models, precedence, health, and emergency controls are validated on every production hardware/site class.

### P2 — Security/observability/resilience gate

- [ ] Component 19: Structured error taxonomy is implemented, verified, operationally owned, and evidenced.
- [ ] Component 20: Tamper-evident audit sink is implemented, verified, operationally owned, and evidenced.
- [ ] Component 21: Metrics exporter is implemented, verified, operationally owned, and evidenced.
- [ ] Component 22: Structured logging and trace propagation is implemented, verified, operationally owned, and evidenced.
- [ ] Component 23: Operator explain endpoint/UI is implemented, verified, operationally owned, and evidenced.
- [ ] Component 24: Dashboards and alerts is implemented, verified, operationally owned, and evidenced.
- [ ] Component 25: Retry/backoff/circuit-breaker policy is implemented, verified, operationally owned, and evidenced.
- [ ] Component 26: Partition/reconnect semantics is implemented, verified, operationally owned, and evidenced.
- [ ] Component 27: Clock-source/time-service strategy is implemented, verified, operationally owned, and evidenced.
- [ ] Component 28: Secret/key isolation model is implemented, verified, operationally owned, and evidenced.
- [ ] Security and resilience game-day demonstrates trust failure, partitions, store failure, time loss, and downstream failure remain bounded and observable.

### P3 — Certification/release/governance gate

- [ ] Component 29: End-to-end integration test harness is implemented, verified, operationally owned, and evidenced.
- [ ] Component 30: Contract/schema validator tests is implemented, verified, operationally owned, and evidenced.
- [ ] Component 31: Concurrency/race test suite is implemented, verified, operationally owned, and evidenced.
- [ ] Component 32: Fault-injection suite is implemented, verified, operationally owned, and evidenced.
- [ ] Component 33: Benchmark/soak/fleet-scale harness is implemented, verified, operationally owned, and evidenced.
- [ ] Component 34: Cross-platform/hardware compatibility matrix is implemented, verified, operationally owned, and evidenced.
- [ ] Component 35: SBOM, dependency pinning, and vulnerability policy is implemented, verified, operationally owned, and evidenced.
- [ ] Component 36: Artifact signing/provenance and reproducible release build is implemented, verified, operationally owned, and evidenced.
- [ ] Component 37: Canary/staged rollout controller is implemented, verified, operationally owned, and evidenced.
- [ ] Component 38: Backup/restore/reconstruction runbook is implemented, verified, operationally owned, and evidenced.
- [ ] Component 39: Incident severity/paging/escalation definitions is implemented, verified, operationally owned, and evidenced.
- [ ] Component 40: Architecture decision record and exception register is implemented, verified, operationally owned, and evidenced.
- [ ] Formal production exit gate is signed for the exact release artifact and no evidence is inherited from a different build/policy/compatibility matrix without revalidation.

