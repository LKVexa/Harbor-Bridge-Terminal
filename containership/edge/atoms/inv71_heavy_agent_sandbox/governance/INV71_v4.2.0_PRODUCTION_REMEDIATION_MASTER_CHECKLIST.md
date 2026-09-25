# INV-71 Heavy Agent Sandbox — Production Remediation Master Checklist

**Baseline:** INV-71 v4.2.0  
**Source audit:** `AUDIT_AFTER.json` / `MISSING_COMPONENTS.md`  
**Scope:** all 90 outstanding checklist controls plus 7 cross-cutting repository/package gaps  
**Purpose:** engineering execution checklist for moving the reference-model package toward a certifiable production microVM sandbox.

> This checklist deliberately treats the Python implementation as a semantic reference model, not as the production isolation boundary. Production evidence must come from the real Firecracker/jailer/host-network/cgroup/artifact/identity/operations path.

## Coverage summary

- Outstanding controls: **90** (**50 MISSING**, **40 PARTIAL**).
- Additional cross-cutting gaps: **7**.
- A control is not complete merely because design prose exists; the release gate should require implementation + tests + machine-readable evidence for the production path.
- Security invariants—tenant isolation, approved-artifact integrity, authenticated/authorized control, default-deny egress, and verified teardown—must fail closed and must not be traded for latency/cost targets.

### Global definition of done

- [ ] **GLOBAL-01** The control has an authoritative, versioned specification and accountable owner.
- [ ] **GLOBAL-02** The production implementation is integrated into the actual Firecracker/jailer/node/control-plane path rather than only the Python model.
- [ ] **GLOBAL-03** Configuration is secure by default, validated before activation, provenance-tracked, and rollback-capable.
- [ ] **GLOBAL-04** Security-sensitive actions are authenticated, authorized, reason-coded, and tamper-evidently audited.
- [ ] **GLOBAL-05** Positive, negative, boundary, concurrency, and fault cases are automated as applicable and leave no leaked host resources.
- [ ] **GLOBAL-06** Performance/resource behavior is bounded and measurable where the control can affect fleet safety or SLOs.
- [ ] **GLOBAL-07** Operator visibility and runbook steps exist for detection, diagnosis, containment, rollback, and recovery.
- [ ] **GLOBAL-08** Machine-readable evidence identifies source/build/config/artifact/environment versions by immutable digest and is consumed by the production release gate.
- [ ] **GLOBAL-09** No unresolved critical/high finding remains; any explicitly accepted residual risk is owner-assigned, approved, compensating-control-backed, and expiry-bounded.
- [ ] **GLOBAL-10** The second audit can change the control to EVIDENCED without relying on inherited framework defaults or unsupported assumptions.

## Recommended evidence bundle layout

```text
evidence/
  release-manifest.json
  traceability.json
  approvals/
  architecture/
  security/
  compatibility/
  integration/
  fault/
  performance/
  observability/
  operations/
  sbom/
  provenance/
  signatures/
```

## Architecture & Scope

### INV-71-C009 — Assign an accountable owner and escalation path for Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** Accountable owner, on-call/escalation path, and authority model are absent.  
**Suggested evidence locations:** `docs/OWNERSHIP.md`, `docs/architecture/`, `governance/approvals/`

#### Targeted engineering checklist

- [ ] **INV-71-C009-IMP-01** Publish a named service ownership record covering product/service owner, microVM runtime owner, host-platform owner, network/security owner, SRE/on-call owner, release authority, and incident commander role.
- [ ] **INV-71-C009-IMP-02** Define a RACI for create/attach/exec/egress-policy/teardown/image-promotion/emergency-disable actions; ensure no single role can both approve and silently bypass security-critical controls.
- [ ] **INV-71-C009-IMP-03** Create primary and secondary 24x7 escalation paths with paging targets, acknowledgment objectives, vendor escalation contacts, and a tested break-glass path.
- [ ] **INV-71-C009-IMP-04** Document authority boundaries: who may change Firecracker/kernel/rootfs pins, network policy, seccomp/device policy, resource ceilings, signing roots, and production rollout state.
- [ ] **INV-71-C009-IMP-05** Run and record an ownership/paging drill proving alerts reach an accountable operator and that escalation proceeds when the primary does not acknowledge.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C009-DES-01** Record the authoritative document path, version, owner, reviewers, and approval date for this control.
- [ ] **INV-71-C009-DES-02** Define the exact scope and out-of-scope boundary, including upstream/downstream ownership and handoff conditions.
- [ ] **INV-71-C009-DES-03** Capture assumptions and residual risks; turn any assumption that can be verified automatically into a preflight/gate check.
- [ ] **INV-71-C009-DES-04** Add the control to architecture review/change-management so later design changes cannot silently invalidate the evidence.

#### Verification and evidence

- [ ] **INV-71-C009-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C009-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C009-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C009-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C009-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C009-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C009-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C009-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C009-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C010 — Approve an architecture decision record for Heavy agent sandbox, its technologies (Firecracker microVM), and its function (Stateful execution, filesystem access, and deeper OS integration).

**Audit status:** `PARTIAL`  
**Existing evidence:** `docs/ADR-0001-heavy-agent-sandbox.md`  
**Observed gap:** ADR exists only as Proposed; no accountable organizational approval record is present.  
**Suggested evidence locations:** `docs/OWNERSHIP.md`, `docs/architecture/`, `governance/approvals/`

#### Targeted engineering checklist

- [ ] **INV-71-C010-IMP-01** Promote ADR-0001 from Proposed only after recording architectural review and explicit approvals from platform, security, SRE, networking, and release owners.
- [ ] **INV-71-C010-IMP-02** Expand the ADR with evaluated alternatives (containers/namespaces, gVisor/Kata, full VMs, WASM), rejection rationale, workload assumptions, trust boundaries, and residual risks.
- [ ] **INV-71-C010-IMP-03** Freeze the production boundary: Firecracker VMM+jailer, host kernel requirements, guest kernel/rootfs, snapshot model, cgroup controls, network enforcement point, identity plane, telemetry plane, and teardown authority.
- [ ] **INV-71-C010-IMP-04** Add quantitative consequences: startup target, per-session memory overhead, host density, snapshot storage, image rollout cost, failure blast radius, and patch cadence.
- [ ] **INV-71-C010-IMP-05** Define ADR supersession rules and require a new review whenever hypervisor class, guest kernel line, host confinement model, or trust boundary changes.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C010-DES-01** Record the authoritative document path, version, owner, reviewers, and approval date for this control.
- [ ] **INV-71-C010-DES-02** Define the exact scope and out-of-scope boundary, including upstream/downstream ownership and handoff conditions.
- [ ] **INV-71-C010-DES-03** Capture assumptions and residual risks; turn any assumption that can be verified automatically into a preflight/gate check.
- [ ] **INV-71-C010-DES-04** Add the control to architecture review/change-management so later design changes cannot silently invalidate the evidence.

#### Verification and evidence

- [ ] **INV-71-C010-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C010-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C010-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C010-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C010-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C010-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C010-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C010-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C010-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Requirements & Semantics

### INV-71-C011 — Translate the source function of Heavy agent sandbox — Stateful execution, filesystem access, and deeper OS integration — into testable SHALL-level requirements.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`  
**Observed gap:** Mandatory behavior exists, but there is no complete SHALL-level requirements specification with acceptance criteria.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C011-IMP-01** Create a normative requirements specification using SHALL/SHALL NOT language for one-session-per-isolation-boundary, clean snapshot start, default-deny egress, resource ceilings, and verified teardown.
- [ ] **INV-71-C011-IMP-02** Assign stable requirement IDs and explicit preconditions, inputs, outputs, postconditions, invariants, and measurable acceptance criteria to each mandatory behavior.
- [ ] **INV-71-C011-IMP-03** Specify security invariants that cannot be traded away: no cross-session residue, no unapproved destination reachability, no privileged host device exposure, and no successful teardown report before destructive verification.
- [ ] **INV-71-C011-IMP-04** Define bounded timing and resource semantics for session create/start/ready/exec/stop/teardown and rejected operations.
- [ ] **INV-71-C011-IMP-05** Map each SHALL to one or more production tests and evidence artifacts so a release gate can prove—not infer—compliance.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C011-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C011-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C011-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C011-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C011-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C011-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C011-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C011-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C011-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C011-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C011-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C011-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C011-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C012 — Define functional requirements for Heavy agent sandbox across cloud, datacenter, near-edge, and far-edge contexts where applicable.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No environment-specific functional requirements for cloud, datacenter, near-edge, or far-edge deployments.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C012-IMP-01** Define deployment profiles for cloud, datacenter, near-edge, and far-edge, including supported CPU virtualization features, storage class, network topology, local control-plane assumptions, and power/thermal envelope.
- [ ] **INV-71-C012-IMP-02** For each profile, declare minimum host kernel, KVM, cgroup v2, filesystem, clock, DNS, entropy, certificate, and image-cache prerequisites.
- [ ] **INV-71-C012-IMP-03** Specify profile-specific availability behavior for disconnected edge sites, constrained bandwidth, image pre-positioning, local policy cache, and delayed telemetry export.
- [ ] **INV-71-C012-IMP-04** Declare unsupported profile combinations explicitly, such as nested virtualization without required KVM features or edge hardware below minimum memory/isolation thresholds.
- [ ] **INV-71-C012-IMP-05** Create an environment qualification test that emits a machine-readable capability report before a node is admitted to the fleet.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C012-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C012-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C012-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C012-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C012-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C012-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C012-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C012-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C012-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C012-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C012-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C012-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C012-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C013 — Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`  
**Observed gap:** Three SLOs are declared, but availability/durability/consistency/determinism objectives are not comprehensively specified.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C013-IMP-01** Define SLOs/SLIs for availability, create-to-ready latency, teardown completion, isolation violations, forbidden-egress violations, durability of audit evidence, policy propagation, and control-plane dependency health.
- [ ] **INV-71-C013-IMP-02** Specify p50/p95/p99 and hard timeout objectives separately for warm-snapshot start, cold-image start, teardown, and policy update.
- [ ] **INV-71-C013-IMP-03** Define consistency/determinism requirements for policy evaluation, snapshot selection, teardown verification, and repeated idempotent control-plane operations.
- [ ] **INV-71-C013-IMP-04** Declare error budgets and zero-budget security invariants separately; a latency budget must never authorize weakening isolation or egress controls.
- [ ] **INV-71-C013-IMP-05** Document measurement windows, aggregation rules, exclusion policy, clock source, and how SLO compliance is computed across sites and tenants.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C013-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C013-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C013-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C013-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C013-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C013-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C013-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C013-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C013-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C013-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C013-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C013-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C013-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C014 — Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Reference exceptions and active/closed behavior exist, but success/partial/degraded/retryable/terminal semantics are not comprehensively modeled.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C014-IMP-01** Define a machine-readable operation outcome model for SUCCESS, PARTIAL, DEGRADED, RETRYABLE_FAILURE, TERMINAL_FAILURE, and SECURITY_REJECTED.
- [ ] **INV-71-C014-IMP-02** For each public operation, state whether partial effects are possible and whether rollback/compensation is mandatory before returning.
- [ ] **INV-71-C014-IMP-03** Classify failures such as snapshot missing, image signature failure, policy service outage, capacity exhaustion, guest crash, teardown timeout, and audit sink outage.
- [ ] **INV-71-C014-IMP-04** Define client behavior for each outcome: retry eligibility, retry-after hint, idempotency key reuse, manual intervention, quarantine, or permanent rejection.
- [ ] **INV-71-C014-IMP-05** Prohibit ambiguous success: session READY and teardown VERIFIED must each have concrete postconditions that can be independently checked.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C014-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C014-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C014-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C014-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C014-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C014-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C014-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C014-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C014-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C014-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C014-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C014-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C014-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C015 — Define lifecycle states and legal state transitions managed or exposed by Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Reference lifecycle has ACTIVE/CLOSED only; production create/starting/ready/draining/failed/reaping transitions are absent.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C015-IMP-01** Define the production state machine with at least REQUESTED, VALIDATING, ALLOCATING, STARTING, READY, RUNNING, DRAINING, STOPPING, VERIFYING_TEARDOWN, CLOSED, FAILED, and QUARANTINED states.
- [ ] **INV-71-C015-IMP-02** Enumerate every legal transition, transition initiator, guard condition, timeout, side effect, and emitted event; reject all unspecified transitions.
- [ ] **INV-71-C015-IMP-03** Specify crash/restart behavior for every intermediate state, including whether ownership can be safely reacquired and what reconciliation action occurs.
- [ ] **INV-71-C015-IMP-04** Represent terminal versus recoverable failure states explicitly and prevent a failed teardown from being collapsed into CLOSED/VERIFIED.
- [ ] **INV-71-C015-IMP-05** Build state-machine property tests proving illegal transitions, duplicate requests, out-of-order callbacks, and stale controllers cannot produce unsafe state.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C015-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C015-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C015-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C015-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C015-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C015-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C015-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C015-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C015-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C015-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C015-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C015-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C015-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C016 — Define versioning and backward-compatibility requirements for Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No supported-version/backward-compatibility policy for INV-71 or its external interfaces.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C016-IMP-01** Define semantic versioning rules separately for control-plane API, event schemas, policy schema, guest image ABI, snapshot format, and implementation release.
- [ ] **INV-71-C016-IMP-02** Publish supported N/N-1 compatibility windows and exact conditions under which backward compatibility is guaranteed or intentionally broken.
- [ ] **INV-71-C016-IMP-03** Require additive schema evolution by default; reserve fields/enums and define unknown-field/unknown-enum handling for older peers.
- [ ] **INV-71-C016-IMP-04** Specify deprecation notice period, telemetry for deprecated use, migration guidance, and enforcement date.
- [ ] **INV-71-C016-IMP-05** Maintain compatibility fixtures that run old clients against new servers and new clients against all supported old servers.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C016-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C016-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C016-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C016-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C016-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C016-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C016-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C016-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C016-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C016-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C016-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C016-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C016-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C017 — Define capacity ceilings, quotas, and fairness semantics relevant to Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Disk/file limits exist in the reference model; CPU, memory, pids, I/O, network, fairness, and fleet ceilings are absent.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C017-IMP-01** Define per-session hard limits for vCPU, memory, PID count, file descriptors, writable bytes/inodes, block IOPS/throughput, network bandwidth/pps, connections, and wall-clock lifetime.
- [ ] **INV-71-C017-IMP-02** Define per-tenant and per-node ceilings for concurrent sessions, aggregate CPU/memory, snapshot cache, image cache, network egress, and control-plane request rate.
- [ ] **INV-71-C017-IMP-03** Choose fairness semantics (e.g., weighted fair share plus hard reservations) and specify behavior under contention, including who is throttled/rejected first.
- [ ] **INV-71-C017-IMP-04** Enforce limits outside the guest using Firecracker configuration plus cgroup v2/host controls; guest self-reporting must not be authoritative.
- [ ] **INV-71-C017-IMP-05** Emit saturation and quota-rejection metrics with tenant-safe identifiers and test that over-limit sessions cannot starve unrelated tenants.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C017-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C017-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C017-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C017-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C017-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C017-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C017-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C017-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C017-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C017-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C017-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C017-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C017-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C018 — Define behavior when network connectivity is intermittent or absent.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No intermittent/offline-network behavior or recovery semantics.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C018-IMP-01** Define which operations are allowed when the control plane, DNS, telemetry backend, artifact registry, policy service, or WAN is unreachable.
- [ ] **INV-71-C018-IMP-02** Create a signed/local policy and artifact cache model with bounded freshness; define exactly when stale cache use is allowed and when execution must fail closed.
- [ ] **INV-71-C018-IMP-03** Specify offline session creation rules for edge sites, including image/snapshot availability, identity validation, revocation freshness, and destination allowlist behavior.
- [ ] **INV-71-C018-IMP-04** Define reconnect reconciliation: upload buffered audit data, refresh policy/identity, detect conflicting controller state, and resolve orphaned sessions.
- [ ] **INV-71-C018-IMP-05** Test prolonged disconnect, clock drift, reconnect storms, duplicate commands, and policy revocation that occurs while a site is offline.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C018-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C018-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C018-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C018-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C018-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C018-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C018-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C018-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C018-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C018-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C018-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C018-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C018-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C019 — Define precedence rules when Heavy agent sandbox requirements conflict with security, residency, SLO, or cost constraints.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No precedence policy for conflicts among security, residency, SLO, and cost constraints.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C019-IMP-01** Publish a deterministic precedence matrix covering security, legal/data-residency, tenant policy, safety, SLO, capacity, cost, and optimization constraints.
- [ ] **INV-71-C019-IMP-02** Declare non-overridable constraints: authentication, artifact integrity, isolation, residency, explicit egress policy, and teardown verification must dominate performance/cost objectives.
- [ ] **INV-71-C019-IMP-03** Define conflict-resolution outcomes and stable reason codes so the same inputs produce the same decision across sites.
- [ ] **INV-71-C019-IMP-04** Require policy changes that alter precedence to pass security/legal review and versioned rollout.
- [ ] **INV-71-C019-IMP-05** Create table-driven tests for pairwise and multi-constraint conflicts, including impossible requests, and verify no hidden fallback bypasses a higher-priority constraint.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C019-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C019-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C019-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C019-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C019-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C019-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C019-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C019-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C019-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C019-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C019-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C019-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C019-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C020 — Maintain a requirements traceability matrix from each Heavy agent sandbox requirement to implementation and verification evidence.

**Audit status:** `PARTIAL`  
**Existing evidence:** `AUDIT_AFTER.json`  
**Observed gap:** A control-status matrix exists, but there is no full requirement-to-production-implementation-to-verification traceability matrix.  
**Suggested evidence locations:** `docs/requirements/INV71_REQUIREMENTS.md`, `evidence/traceability.json`

#### Targeted engineering checklist

- [ ] **INV-71-C020-IMP-01** Create a requirements traceability matrix linking every INV-71 requirement ID to design artifact, source/config implementation, test case, runtime signal, release evidence, and accountable owner.
- [ ] **INV-71-C020-IMP-02** Make traceability bidirectional: every production component/test must reference the requirement(s) it satisfies, and orphaned code/tests must be flagged.
- [ ] **INV-71-C020-IMP-03** Store immutable evidence digests and release identifiers rather than only paths so the matrix proves exactly which artifact was evaluated.
- [ ] **INV-71-C020-IMP-04** Automate coverage checks in CI to fail when a requirement has no implementation or verification edge.
- [ ] **INV-71-C020-IMP-05** Version and sign the traceability export as part of production certification.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C020-DES-01** Write normative SHALL/SHALL NOT statements and measurable acceptance criteria for the control.
- [ ] **INV-71-C020-DES-02** Define success, failure, boundary, timeout, and conflict behavior with stable reason/error codes where externally observable.
- [ ] **INV-71-C020-DES-03** Add requirement IDs to the traceability matrix and reference them from implementation, tests, telemetry, and operator documentation.
- [ ] **INV-71-C020-DES-04** Review the requirement for deterministic behavior across local/remote dependency placement and all supported deployment profiles.

#### Verification and evidence

- [ ] **INV-71-C020-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C020-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C020-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C020-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C020-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C020-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C020-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C020-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C020-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Interfaces & Integration

### INV-71-C021 — Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `README.md`, `schemas/`  
**Observed gap:** Three logical record interfaces are named; hypervisor, image, device, filesystem, network, identity, and control-plane boundaries are not fully enumerated.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C021-IMP-01** Inventory every boundary: workload API, scheduler/control plane, Firecracker API socket, jailer process, KVM device, guest console/vsock, block devices, TAP/veth, DNS/proxy/firewall, image/snapshot store, identity/key service, audit/metrics/log/trace sinks, and operator interfaces.
- [ ] **INV-71-C021-IMP-02** For each boundary document protocol, direction, trust level, caller/callee identity, data classification, timeout, size limits, and ownership.
- [ ] **INV-71-C021-IMP-03** Explicitly record host filesystem paths, UNIX sockets, device nodes, namespaces, mounts, cgroups, and kernel interfaces touched by the runtime.
- [ ] **INV-71-C021-IMP-04** Create a data-flow diagram showing where untrusted guest-controlled bytes cross parsers or privilege boundaries.
- [ ] **INV-71-C021-IMP-05** Fail architecture review when an implementation introduces an undeclared boundary or privileged channel.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C021-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C021-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C021-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C021-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C021-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C021-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C021-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C021-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C021-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C021-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C021-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C021-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C021-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C022 — Use versioned typed schemas for all externally visible Heavy agent sandbox contracts.

**Audit status:** `PARTIAL`  
**Existing evidence:** `schemas/`  
**Observed gap:** Versioned JSON Schemas exist for three logical records, but the complete external API/transport contract is not defined.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C022-IMP-01** Define versioned typed schemas for session create/status/delete, exec/attach if supported, egress decision, policy distribution, teardown evidence, health/readiness, audit event, and configuration status.
- [ ] **INV-71-C022-IMP-02** Use a single canonical serialization per transport and publish deterministic canonicalization rules for data that is signed or hashed.
- [ ] **INV-71-C022-IMP-03** Mark required/optional fields, enum evolution rules, length/range constraints, normalization, redaction class, and compatibility behavior.
- [ ] **INV-71-C022-IMP-04** Generate validators/client types from schemas where practical and prohibit ad-hoc unvalidated dictionaries at trust boundaries.
- [ ] **INV-71-C022-IMP-05** Add golden positive/negative fixtures and CI schema-compatibility checks against all supported versions.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C022-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C022-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C022-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C022-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C022-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C022-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C022-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C022-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C022-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C022-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C022-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C022-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C022-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C023 — Define authentication requirements at each Heavy agent sandbox boundary.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No authentication design for session, egress, teardown, hypervisor, image, node, or control-plane boundaries.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C023-IMP-01** Define an authentication matrix for user/operator, scheduler, node agent, image builder, artifact registry, policy service, audit sink, and inter-site/control-plane peers.
- [ ] **INV-71-C023-IMP-02** Use workload/node identities bound to mutually authenticated transport (for example SPIFFE-compatible identities or an equivalent PKI design) rather than IP/source-address trust.
- [ ] **INV-71-C023-IMP-03** Define certificate/token issuance, audience, lifetime, rotation, revocation, replay resistance, bootstrap trust roots, and clock-skew tolerance.
- [ ] **INV-71-C023-IMP-04** Require host/node identity before accepting session creation and artifact identity before loading executable content.
- [ ] **INV-71-C023-IMP-05** Test expired, revoked, wrong-audience, wrong-tenant, forged-chain, replayed, clock-skewed, and anonymous requests and verify fail-closed behavior.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C023-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C023-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C023-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C023-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C023-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C023-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C023-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C023-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C023-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C023-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C023-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C023-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C023-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C024 — Define authorization and explicit capability requirements at each Heavy agent sandbox boundary.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Exact-host egress authorization exists; capabilities and authorization at every production boundary are not defined.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C024-IMP-01** Create an explicit authorization/capability model for create, inspect, exec, network-policy update, attach, stop, teardown, quarantine, artifact promotion, and emergency operations.
- [ ] **INV-71-C024-IMP-02** Make default-deny the base rule; prohibit implicit administrator inheritance and wildcard tenant access unless explicitly justified and audited.
- [ ] **INV-71-C024-IMP-03** Bind authorization to authenticated principal, tenant/workload, environment/site, requested capability, resource attributes, and policy version.
- [ ] **INV-71-C024-IMP-04** Separate control-plane capability to request guest work from host capability to manipulate Firecracker/KVM/network devices.
- [ ] **INV-71-C024-IMP-05** Emit reason-coded allow/deny decisions and test privilege escalation through role confusion, tenant-ID substitution, stale policy, and confused-deputy paths.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C024-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C024-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C024-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C024-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C024-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C024-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C024-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C024-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C024-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C024-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C024-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C024-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C024-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C025 — Define timeout, cancellation, retry, idempotency, and backpressure semantics for Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No complete timeout, cancellation, retry, idempotency, or backpressure semantics.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C025-IMP-01** Specify per-operation deadlines for create, snapshot restore, policy fetch, exec/attach, stop, teardown, audit delivery, and artifact retrieval.
- [ ] **INV-71-C025-IMP-02** Define cancellation semantics, including which operations are cancellable, what rollback occurs, and how a caller observes final disposition after cancellation races.
- [ ] **INV-71-C025-IMP-03** Assign idempotency keys and deduplication windows to all mutating control-plane calls; define exact replay response semantics.
- [ ] **INV-71-C025-IMP-04** Classify retry safety by operation and implement bounded exponential backoff with jitter only for retry-safe failures.
- [ ] **INV-71-C025-IMP-05** Define server-side backpressure signals, queue limits, Retry-After behavior, and overload rejection codes; prove retries cannot amplify an outage.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C025-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C025-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C025-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C025-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C025-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C025-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C025-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C025-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C025-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C025-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C025-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C025-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C025-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C026 — Define structured failure codes and machine-readable error details for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Typed Python exceptions exist locally, but no stable external machine-readable error-code contract exists.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C026-IMP-01** Create a stable error namespace partitioned by validation, authentication, authorization, policy, capacity, dependency, artifact, hypervisor, guest, network, teardown, and internal failures.
- [ ] **INV-71-C026-IMP-02** For each code specify retryability, HTTP/gRPC-equivalent status if applicable, operator action, user-safe message, and secret-safe diagnostic fields.
- [ ] **INV-71-C026-IMP-03** Include correlation ID, operation ID, session ID, policy/config version, and causal chain without exposing credentials or cross-tenant details.
- [ ] **INV-71-C026-IMP-04** Never overload one error code with materially different recovery actions; unknown internal failures must map to a safe generic external code while retaining privileged diagnostics.
- [ ] **INV-71-C026-IMP-05** Add contract tests ensuring every thrown/returned production error is mapped and schema-valid.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C026-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C026-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C026-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C026-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C026-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C026-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C026-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C026-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C026-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C026-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C026-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C026-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C026-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C027 — Define compatibility behavior when peers use different supported versions.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No mixed-version peer compatibility behavior.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C027-IMP-01** Define handshake/negotiation behavior for API, event, policy, snapshot, and image compatibility when peers run different supported versions.
- [ ] **INV-71-C027-IMP-02** Specify feature discovery/capability negotiation and prohibit silent activation of features an older peer cannot safely interpret.
- [ ] **INV-71-C027-IMP-03** Define rolling-upgrade ordering and the maximum skew allowed between controller, node agent, image format, and schema versions.
- [ ] **INV-71-C027-IMP-04** Specify downgrade behavior and what state/artifacts are incompatible after a forward migration.
- [ ] **INV-71-C027-IMP-05** Run mixed-version matrices through create/start/egress/teardown/reconcile flows before certifying a release.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C027-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C027-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C027-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C027-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C027-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C027-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C027-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C027-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C027-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C027-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C027-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C027-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C027-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C028 — Document payload, concurrency, queue, connection, or resource limits at Heavy agent sandbox interfaces.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Disk/file/history limits exist; payload, connection, concurrency, CPU, memory, process, I/O, and queue limits are incomplete.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C028-IMP-01** Publish explicit maximum request/response/event sizes, metadata lengths, allowlist entries, environment entries, mount count, device count, and diagnostic payload size.
- [ ] **INV-71-C028-IMP-02** Define per-principal/session concurrency, outstanding operation, connection, stream, and queue limits.
- [ ] **INV-71-C028-IMP-03** Enforce limits before expensive parsing/allocation when possible to mitigate memory and CPU denial of service.
- [ ] **INV-71-C028-IMP-04** Define behavior at soft versus hard limits, including throttling, rejection, shedding, and audit/metric emission.
- [ ] **INV-71-C028-IMP-05** Fuzz and load-test every limit boundary at N-1/N/N+1 and with concurrent tenants to prove isolation and bounded memory.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C028-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C028-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C028-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C028-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C028-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C028-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C028-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C028-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C028-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C028-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C028-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C028-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C028-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C029 — Provide reference examples and conformance fixtures for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `tests/test_sandbox.py`, `schemas/`  
**Observed gap:** Tests and schemas provide examples, but no formal adjacent-layer conformance fixture bundle exists.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C029-IMP-01** Create a versioned conformance-fixture package containing canonical session, egress, teardown, error, health, audit, policy, and configuration examples.
- [ ] **INV-71-C029-IMP-02** Include golden serialized bytes where canonical encoding/signing matters plus invalid fixtures for every required validation rule.
- [ ] **INV-71-C029-IMP-03** Provide a minimal fake adjacent-layer harness for INV-69, INV-24, INV-26, and GAP-09 interactions.
- [ ] **INV-71-C029-IMP-04** Include expected state transitions, emitted events, metrics, and audit hashes for deterministic scenarios.
- [ ] **INV-71-C029-IMP-05** Publish fixture version and digest and require every supported implementation to run the same suite.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C029-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C029-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C029-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C029-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C029-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C029-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C029-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C029-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C029-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C029-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C029-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C029-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C029-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C030 — Create automated integration tests proving Heavy agent sandbox interoperates with adjacent architectural layers.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No automated integration tests with adjacent architectural layers.  
**Suggested evidence locations:** `schemas/`, `api/`, `fixtures/conformance/`, `tests/integration/`

#### Targeted engineering checklist

- [ ] **INV-71-C030-IMP-01** Build automated integration tests across INV-69 workload routing, INV-24 microVM runtime, INV-26 snapshotting, and GAP-09 observability rather than mocking all boundaries.
- [ ] **INV-71-C030-IMP-02** Exercise create→restore→ready→work→egress decision→teardown→verification end to end with real transport serialization.
- [ ] **INV-71-C030-IMP-03** Cover dependency failure, timeout, partial response, duplicate request, version skew, and authentication/authorization rejection.
- [ ] **INV-71-C030-IMP-04** Run tests on representative Linux/KVM hosts and at least one production-equivalent network/storage configuration.
- [ ] **INV-71-C030-IMP-05** Capture machine-readable evidence, component versions, host capabilities, logs, traces, and artifact digests for each integration run.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C030-DES-01** Document trust direction, authentication, authorization, timeout, idempotency, resource limits, and compatibility semantics for every interface touched by this control.
- [ ] **INV-71-C030-DES-02** Use versioned typed schemas and canonical validation at the earliest trust boundary; reject ambiguous or unbounded inputs.
- [ ] **INV-71-C030-DES-03** Provide positive, negative, boundary, and mixed-version conformance fixtures.
- [ ] **INV-71-C030-DES-04** Exercise the interface through real transports/adapters in integration tests, not only in-process mocks.

#### Verification and evidence

- [ ] **INV-71-C030-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C030-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C030-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C030-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C030-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C030-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C030-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C030-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C030-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Implementation & Configuration

### INV-71-C031 — Select and pin approved implementations, versions, or specifications for Heavy agent sandbox: Firecracker microVM.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No pinned Firecracker, kernel, jailer, rootfs/base-image, or snapshot format versions.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C031-IMP-01** Pin exact approved Firecracker and jailer versions, guest kernel build/config, rootfs/base-image digest, snapshot format, host kernel baseline, and critical runtime libraries.
- [ ] **INV-71-C031-IMP-02** Record CPU vendor/model/microcode and KVM feature prerequisites that affect snapshot portability or isolation guarantees.
- [ ] **INV-71-C031-IMP-03** Maintain an approved-version manifest with cryptographic digests and explicit compatibility relationships among VMM, kernel, rootfs, snapshots, and node agent.
- [ ] **INV-71-C031-IMP-04** Define update policy for security releases and prohibit floating tags/latest aliases in production build or deployment inputs.
- [ ] **INV-71-C031-IMP-05** Add CI and node-start checks that reject unapproved version/digest combinations.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C031-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C031-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C031-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C031-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C031-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C031-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C031-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C031-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C031-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C031-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C031-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C031-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C031-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C032 — Separate immutable artifacts from mutable configuration and state for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Immutable base semantics are modeled, but no production artifact/configuration/state layout or signed immutable image set exists.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C032-IMP-01** Define an immutable artifact hierarchy for node agent binary, Firecracker/jailer, kernel, rootfs, policy bundle, seccomp profile, and snapshot layers, each addressed by digest.
- [ ] **INV-71-C032-IMP-02** Place mutable per-session state only in dedicated writable overlays/tmpfs/ephemeral block devices with explicit lifecycle ownership.
- [ ] **INV-71-C032-IMP-03** Prohibit runtime mutation of signed base artifacts; rebuild and repromote artifacts instead of editing in place.
- [ ] **INV-71-C032-IMP-04** Document storage locations, permissions, mount flags, ownership, cleanup policy, and cache eviction separately for immutable artifacts and mutable state.
- [ ] **INV-71-C032-IMP-05** Test that teardown removes all session-owned overlays and that a subsequent session mounts only approved immutable bases plus a fresh writable layer.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C032-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C032-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C032-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C032-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C032-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C032-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C032-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C032-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C032-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C032-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C032-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C032-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C032-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C033 — Define declarative configuration and secure defaults for Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No declarative production configuration format with secure defaults.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C033-IMP-01** Create a typed declarative production configuration schema for host/runtime, session defaults, resource ceilings, network policy, artifact references, telemetry, and feature gates.
- [ ] **INV-71-C033-IMP-02** Define secure defaults: default-deny egress, no host devices/mounts, non-root service, bounded resources, no debug console, authenticated endpoints, and fail-closed artifact verification.
- [ ] **INV-71-C033-IMP-03** Mark security-sensitive fields as immutable-at-runtime or privileged-change-only and define minimum/maximum ranges.
- [ ] **INV-71-C033-IMP-04** Support deterministic config rendering with no environment-dependent hidden defaults.
- [ ] **INV-71-C033-IMP-05** Ship an example hardened baseline plus schema documentation and reject unknown fields unless an explicit forward-compatibility policy permits them.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C033-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C033-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C033-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C033-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C033-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C033-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C033-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C033-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C033-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C033-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C033-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C033-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C033-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C034 — Validate configuration before activation and fail closed on security-critical errors.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Reference inputs fail closed, but production configuration validation/activation is not implemented.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C034-IMP-01** Perform syntactic, semantic, cross-field, environment-capability, and cryptographic-reference validation before a configuration becomes active.
- [ ] **INV-71-C034-IMP-02** Validate network rules, resource budgets, paths, device lists, artifact digests, certificate references, and incompatible feature combinations.
- [ ] **INV-71-C034-IMP-03** Stage configuration and atomically activate only after all required components acknowledge validation; retain the previous known-good version.
- [ ] **INV-71-C034-IMP-04** Fail closed on missing/invalid security-critical settings and distinguish operator configuration errors from dependency outages.
- [ ] **INV-71-C034-IMP-05** Create negative tests for malformed, oversized, conflicting, stale, unsigned, and privilege-escalating configuration.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C034-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C034-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C034-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C034-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C034-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C034-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C034-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C034-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C034-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C034-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C034-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C034-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C034-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C035 — Support site- and environment-specific configuration without rebuilding immutable artifacts.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No site/environment overlay configuration mechanism independent of immutable artifacts.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C035-IMP-01** Define layered configuration precedence for immutable defaults, environment profile, site overlay, tenant policy, and per-session request without rebuilding binaries/images.
- [ ] **INV-71-C035-IMP-02** Constrain overlays to an allowlisted field set so a site cannot silently disable global security invariants.
- [ ] **INV-71-C035-IMP-03** Version, sign, and independently roll back overlays; include source and effective-config hash in session/audit records.
- [ ] **INV-71-C035-IMP-04** Support offline edge-site overlay caching with bounded freshness and conflict detection on reconnect.
- [ ] **INV-71-C035-IMP-05** Test deterministic merge behavior, forbidden overrides, missing layers, duplicate keys, and rollback to prior effective configuration.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C035-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C035-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C035-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C035-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C035-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C035-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C035-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C035-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C035-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C035-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C035-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C035-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C035-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C036 — Record configuration provenance, version, author, and activation time.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No configuration provenance/author/version/activation-time record.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C036-IMP-01** Attach provenance metadata to every active configuration: config ID/version, source repository/commit, author/automation identity, review/approval IDs, signature/digest, build timestamp, and activation timestamp.
- [ ] **INV-71-C036-IMP-02** Record the exact effective-config digest on every session and security-sensitive audit event.
- [ ] **INV-71-C036-IMP-03** Keep append-only activation/deactivation history with actor, reason, previous/new digest, rollout cohort, and rollback linkage.
- [ ] **INV-71-C036-IMP-04** Expose config provenance through an authenticated operator status endpoint without leaking secrets.
- [ ] **INV-71-C036-IMP-05** Verify during incident response that a session's behavior can be reconstructed from retained config provenance.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C036-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C036-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C036-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C036-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C036-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C036-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C036-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C036-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C036-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C036-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C036-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C036-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C036-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C037 — Apply atomic or transactional configuration updates where partial application is unsafe.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Reference filesystem updates are copy-then-commit under a lock; production configuration transactions are absent.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C037-IMP-01** Define configuration transaction boundaries spanning node agent, firewall/proxy, cgroups, Firecracker parameters, and policy cache where partial application would be unsafe.
- [ ] **INV-71-C037-IMP-02** Implement prepare/validate then commit semantics or an equivalent generation-switch model; never mutate live security state field-by-field without rollback.
- [ ] **INV-71-C037-IMP-03** Assign monotonically increasing generations and require all participating components to report the same committed generation.
- [ ] **INV-71-C037-IMP-04** On failure, restore the previous generation and quarantine nodes with indeterminate mixed state.
- [ ] **INV-71-C037-IMP-05** Fault-inject process death, disk-full, timeout, and network loss at every transaction phase and verify no partially weakened configuration becomes active.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C037-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C037-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C037-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C037-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C037-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C037-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C037-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C037-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C037-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C037-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C037-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C037-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C037-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C038 — Define automatic and operator-driven rollback for failed Heavy agent sandbox changes.

**Audit status:** `PARTIAL`  
**Existing evidence:** `README.md`  
**Observed gap:** Rollback is described conceptually around previous evidence/snapshots; no deployable automatic/operator rollback mechanism exists.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C038-IMP-01** Define automatic rollback triggers for crash-loop, startup regression, SLO breach, isolation/egress anomaly, failed health check, and incompatible config/artifact activation.
- [ ] **INV-71-C038-IMP-02** Maintain previous known-good binary/config/image/snapshot generations and verify their signatures before rollback.
- [ ] **INV-71-C038-IMP-03** Support operator-initiated rollback with scoped cohort/site/tenant selection, reason recording, and two-person approval for security-sensitive downgrades.
- [ ] **INV-71-C038-IMP-04** Specify state compatibility and migration constraints so rollback never reinterprets newer state unsafely.
- [ ] **INV-71-C038-IMP-05** Run regular rollback drills and measure detection-to-restoration time against an explicit objective.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C038-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C038-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C038-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C038-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C038-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C038-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C038-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C038-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C038-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C038-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C038-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C038-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C038-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C039 — Keep credentials and secret material out of ordinary Heavy agent sandbox configuration and diagnostics.

**Audit status:** `PARTIAL`  
**Existing evidence:** `README.md`  
**Observed gap:** No credentials are embedded in ordinary repo configuration, but a production secret injection/redaction mechanism is absent.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C039-IMP-01** Define a secret delivery mechanism using short-lived workload/node credentials, mounted/streamed only to the component that requires them; do not store secrets in ordinary config files, images, snapshots, logs, or CLI arguments.
- [ ] **INV-71-C039-IMP-02** Separate guest secrets from host/control-plane secrets and prevent guest access to node identity, signing keys, registry credentials, and telemetry credentials.
- [ ] **INV-71-C039-IMP-03** Integrate secret redaction into structured logs, traces, crash dumps, audit diagnostics, and operator explain views.
- [ ] **INV-71-C039-IMP-04** Define rotation/revocation behavior for active sessions and what happens when the secret provider is unavailable.
- [ ] **INV-71-C039-IMP-05** Add secret-scanning plus runtime tests that inspect process environment, argv, mounted files, snapshots, core dumps, and telemetry for leakage.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C039-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C039-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C039-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C039-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C039-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C039-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C039-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C039-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C039-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C039-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C039-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C039-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C039-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C040 — Provide a deterministic bootstrap path from an empty node/environment to healthy Heavy agent sandbox operation.

**Audit status:** `PARTIAL`  
**Existing evidence:** `README.md`, `tools/repo_audit.py`  
**Observed gap:** Local test/audit bootstrap is deterministic, but empty-node-to-production-health bootstrap is not implemented.  
**Suggested evidence locations:** `config/schema/`, `deploy/`, `artifacts/manifest.json`, `bootstrap/`

#### Targeted engineering checklist

- [ ] **INV-71-C040-IMP-01** Automate empty-node bootstrap: host prerequisite validation, package/artifact installation, trust-root provisioning, service identity bootstrap, cgroup/network setup, runtime configuration, image/snapshot prefetch, and health registration.
- [ ] **INV-71-C040-IMP-02** Make bootstrap idempotent and resumable after interruption without leaving privileged stale resources or partially trusted state.
- [ ] **INV-71-C040-IMP-03** Verify all downloaded artifacts before use and pin every bootstrap dependency by version/digest.
- [ ] **INV-71-C040-IMP-04** Generate a machine-readable node qualification report covering KVM, CPU features, kernel config, time sync, disk, network enforcement, identity, and telemetry reachability.
- [ ] **INV-71-C040-IMP-05** Test bootstrap from a clean production-equivalent host and destructive re-bootstrap after partial failure.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C040-DES-01** Express production state declaratively where possible, pin immutable artifact inputs by digest, and separate mutable state from immutable artifacts.
- [ ] **INV-71-C040-DES-02** Use fail-closed validation and atomic/generation-based activation for security-sensitive changes.
- [ ] **INV-71-C040-DES-03** Define rollback/recovery behavior and preserve a verifiable previous known-good generation.
- [ ] **INV-71-C040-DES-04** Record provenance and effective-version/digest in runtime status and audit evidence.

#### Verification and evidence

- [ ] **INV-71-C040-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C040-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C040-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C040-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C040-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C040-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C040-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C040-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C040-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Security, Trust & Isolation

### INV-71-C042 — Apply least privilege to every identity and capability used by Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Reference privileges are narrow for paths/egress; production host identities, devices, syscalls, mounts, and control-plane permissions are not defined.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C042-IMP-01** Inventory every service/user/group/capability used by controller, node agent, Firecracker, jailer, network helper, image manager, and telemetry exporters.
- [ ] **INV-71-C042-IMP-02** Run host services as dedicated non-root identities; drop Linux capabilities not strictly required and document any retained capability with rationale.
- [ ] **INV-71-C042-IMP-03** Restrict KVM, TAP/TUN, cgroup, block-device, namespace, and filesystem permissions to the minimum helper process rather than the broad service.
- [ ] **INV-71-C042-IMP-04** Separate operator read, execute, policy-edit, artifact-promote, quarantine, and break-glass privileges.
- [ ] **INV-71-C042-IMP-05** Continuously test that compromised node-agent subprocesses cannot access unrelated tenants, signing keys, host root, or unrestricted network/device interfaces.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C042-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C042-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C042-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C042-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C042-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C042-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C042-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C042-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C042-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C042-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C042-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C042-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C042-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C043 — Eliminate ambient filesystem, network, device, kernel, and secret authority wherever Heavy agent sandbox permits.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Path and egress authority are constrained in the model; ambient kernel/device/secret/filesystem authority is not eliminated by a production boundary.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C043-IMP-01** Remove ambient host filesystem access by using a minimal jail root, explicit read-only bind mounts, no host home/runtime directories, and no arbitrary path passthrough.
- [ ] **INV-71-C043-IMP-02** Remove ambient network authority: default-deny host-side namespace/firewall/proxy, no unrestricted host networking, and explicit destination/port/protocol policy.
- [ ] **INV-71-C043-IMP-03** Expose only required devices; prohibit generic host block devices, privileged character devices, host sockets, and debug interfaces.
- [ ] **INV-71-C043-IMP-04** Apply a minimized seccomp/syscall profile and host kernel hardening appropriate to Firecracker/jailer; document every exception.
- [ ] **INV-71-C043-IMP-05** Ensure secrets are capability-scoped and not present in inherited environment, global filesystem, metadata services, or shared agent credentials.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C043-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C043-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C043-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C043-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C043-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C043-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C043-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C043-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C043-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C043-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C043-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C043-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C043-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C044 — Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No node/peer/artifact/provider/control-plane authentication or attestation implementation.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C044-IMP-01** Authenticate node agents and control-plane peers with unique cryptographic identities and mutual authentication before accepting commands or status.
- [ ] **INV-71-C044-IMP-02** Attest boot/runtime state where required, binding node identity to approved host image/kernel/runtime measurements and hardware identity.
- [ ] **INV-71-C044-IMP-03** Authenticate artifact registries/builders and verify that policy/image/snapshot publishers are authorized principals, not merely reachable endpoints.
- [ ] **INV-71-C044-IMP-04** Define bootstrap trust, rotation, revocation, lost-key, compromised-node, and re-enrollment procedures.
- [ ] **INV-71-C044-IMP-05** Reject and alert on identity mismatch, duplicate node identity, expired/revoked credentials, failed attestation, or artifact publisher outside the approved trust domain.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C044-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C044-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C044-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C044-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C044-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C044-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C044-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C044-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C044-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C044-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C044-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C044-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C044-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C045 — Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No signature, digest, provenance, SBOM, or approved-version verification pipeline for executable/policy artifacts.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C045-IMP-01** Generate SBOMs for node agent, Firecracker/jailer bundle, guest kernel/rootfs, and image/snapshot build dependencies.
- [ ] **INV-71-C045-IMP-02** Sign executable artifacts, rootfs/images, policy bundles, and release manifests; verify signature plus cryptographic digest before activation/load.
- [ ] **INV-71-C045-IMP-03** Record build provenance with source revision, builder identity, build recipe, dependency digests, and reproducibility status; target a SLSA-style provenance model or equivalent.
- [ ] **INV-71-C045-IMP-04** Enforce an approved-version policy that can revoke a digest immediately after vulnerability or compromise discovery.
- [ ] **INV-71-C045-IMP-05** Test tampered artifact, wrong signer, expired trust root, digest mismatch, unapproved version, and replayed old-but-valid artifact scenarios.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C045-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C045-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C045-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C045-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C045-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C045-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C045-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C045-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C045-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C045-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C045-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C045-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C045-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C046 — Enforce tenant/workload isolation across Heavy agent sandbox execution, memory, state, network, and device boundaries as applicable.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`, `tests/test_sandbox.py`  
**Observed gap:** Cross-session clean-start semantics are tested in memory; real VM memory/state/network/device isolation evidence is absent.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C046-IMP-01** Run each tenant/workload session in a distinct microVM boundary with no shared writable guest filesystem, process namespace, memory, network namespace, or device state.
- [ ] **INV-71-C046-IMP-02** Define and enforce CPU/memory/cgroup placement and cache/co-tenancy policy where side-channel or noisy-neighbor risk matters.
- [ ] **INV-71-C046-IMP-03** Use per-session block overlays and network namespaces/interfaces; prohibit shared host mounts and reused writable snapshots.
- [ ] **INV-71-C046-IMP-04** Verify device model exposure is minimal and that vsock/console/control channels are session-bound and not cross-routable.
- [ ] **INV-71-C046-IMP-05** Create destructive cross-session residue tests for memory, disk blocks, page cache-visible artifacts, network state, file descriptors, device state, and host helper state.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C046-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C046-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C046-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C046-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C046-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C046-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C046-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C046-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C046-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C046-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C046-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C046-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C046-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C047 — Encrypt sensitive Heavy agent sandbox data in transit and at rest with managed key rotation.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No in-transit/at-rest encryption design with managed key rotation.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C047-IMP-01** Classify sensitive data and enumerate every in-transit and at-rest path: control API, artifact download, policy distribution, audit/telemetry, guest secrets, snapshots, writable overlays, and backups.
- [ ] **INV-71-C047-IMP-02** Require modern mutually authenticated encryption for control-plane and service traffic; define approved protocol/cipher policy and certificate rotation.
- [ ] **INV-71-C047-IMP-03** Encrypt sensitive persistent artifacts/state at rest with keys separated by environment/tenant where required; keep key material outside images/snapshots.
- [ ] **INV-71-C047-IMP-04** Define key lifecycle: generation, storage, access policy, rotation, revocation, backup/recovery, compromise response, and cryptographic erase strategy.
- [ ] **INV-71-C047-IMP-05** Test certificate/key rotation during live operation and prove stale/revoked credentials cannot continue to authorize new sessions.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C047-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C047-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C047-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C047-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C047-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C047-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C047-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C047-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C047-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C047-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C047-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C047-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C047-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C048 — Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No fail-closed/degraded policy for identity, attestation, policy, key, or time service outages.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C048-IMP-01** For identity, attestation, policy, key, and trusted-time dependencies, classify which operations must fail closed, which existing sessions may continue, and for how long.
- [ ] **INV-71-C048-IMP-02** Define bounded cached-credential/policy validity and prevent indefinite operation on stale trust state.
- [ ] **INV-71-C048-IMP-03** Treat inability to verify a new artifact, new identity, or new security policy as a hard deny for new trust decisions.
- [ ] **INV-71-C048-IMP-04** Define clock-loss behavior for certificate validity, token expiry, audit ordering, and anti-replay; include monotonic-clock safeguards where possible.
- [ ] **INV-71-C048-IMP-05** Exercise dependency outages and partitions in tests, including recovery and revocation that occurred during the outage.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C048-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C048-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C048-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C048-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C048-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C048-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C048-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C048-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C048-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C048-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C048-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C048-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C048-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C049 — Emit tamper-evident audit events for security-sensitive Heavy agent sandbox operations.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`, `tests/test_sandbox.py`  
**Observed gap:** Reference audit events are hash chained and tamper-detecting in process; they are unsigned, non-durable, and not externally anchored.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C049-IMP-01** Define a durable security audit schema covering authentication, authorization, session lifecycle, policy decisions, artifact selection/verification, egress allow/deny, privileged operations, quarantine, and teardown verification.
- [ ] **INV-71-C049-IMP-02** Hash-chain or Merkle-link records per stream and cryptographically sign/anchor stream checkpoints outside the node so local compromise cannot silently rewrite history.
- [ ] **INV-71-C049-IMP-03** Use authenticated transport to an append-only/WORM-capable sink with backpressure/spooling rules that cannot deadlock or silently drop security events.
- [ ] **INV-71-C049-IMP-04** Include actor, tenant-safe resource identifiers, node, operation, policy/config/artifact versions, reason code, timestamp source, and correlation IDs; redact secrets.
- [ ] **INV-71-C049-IMP-05** Build verification tooling that detects deletion, insertion, mutation, reordering, duplicate sequence, broken signature, and missing checkpoint continuity.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C049-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C049-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C049-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C049-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C049-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C049-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C049-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C049-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C049-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C049-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C049-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C049-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C049-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C050 — Run adversarial tests for privilege escalation, injection, replay, spoofing, escape, side channels, and resource exhaustion.

**Audit status:** `PARTIAL`  
**Existing evidence:** `tests/test_sandbox.py`  
**Observed gap:** Traversal, forbidden egress, quotas, lifecycle misuse, and audit tampering are tested; escape, injection, replay, spoofing, side-channel, and hypervisor adversarial tests are absent.  
**Suggested evidence locations:** `security/`, `policy/`, `evidence/security/`, `tests/security/`

#### Targeted engineering checklist

- [ ] **INV-71-C050-IMP-01** Build privilege-escalation tests against jailer permissions, Linux capabilities, seccomp, device nodes, host mounts, KVM access, namespace helpers, and control-plane APIs.
- [ ] **INV-71-C050-IMP-02** Fuzz/inject malformed guest and control-plane input into API parsers, image metadata, policy/config parsers, vsock/console protocols, and network enforcement components.
- [ ] **INV-71-C050-IMP-03** Test replay/spoofing with captured control commands, tokens, teardown records, policy updates, node identities, DNS responses, and audit messages.
- [ ] **INV-71-C050-IMP-04** Run microVM escape-oriented tests against supported Firecracker/kernel combinations and track relevant CVEs/advisories to regression cases.
- [ ] **INV-71-C050-IMP-05** Exercise resource exhaustion and side-channel-relevant scenarios: fork/PID bomb, memory pressure, I/O flood, connection flood, log amplification, CPU saturation, cache/co-tenancy tests where required.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C050-DES-01** Map the work to a concrete threat-model entry and specify prevention, detection, containment, and recovery controls.
- [ ] **INV-71-C050-DES-02** Apply least privilege/default deny and enforce the control outside the untrusted guest whenever feasible.
- [ ] **INV-71-C050-DES-03** Generate tamper-evident evidence containing principal, resource, policy/config/artifact versions, reason code, and correlation ID without secrets.
- [ ] **INV-71-C050-DES-04** Run adversarial negative tests and preserve minimized regression cases for every security defect found.

#### Verification and evidence

- [ ] **INV-71-C050-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C050-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C050-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C050-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C050-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C050-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C050-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C050-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C050-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Resilience & Failure Handling

### INV-71-C051 — Enumerate component, process, VM, node, site, network, provider, dependency, and control-plane failures affecting Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`, `docs/THREAT_MODEL.md`  
**Observed gap:** Several failures are listed, but there is no exhaustive component/process/VM/node/site/provider/control-plane failure matrix.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C051-IMP-01** Create an FMEA-style failure matrix spanning controller process, node agent, jailer, Firecracker process, guest kernel, guest workload, cgroup helper, network namespace/firewall/proxy, DNS, storage, snapshot/image cache, identity/key/policy/time services, telemetry, node, rack/site, WAN, and provider.
- [ ] **INV-71-C051-IMP-02** For each failure record detection signal, blast radius, state ambiguity, retry safety, automatic recovery, operator action, data-loss/isolation risk, and maximum tolerated duration.
- [ ] **INV-71-C051-IMP-03** Identify correlated failures and shared dependencies that invalidate independent-failure assumptions.
- [ ] **INV-71-C051-IMP-04** Map each failure to a fault-injection scenario and an observable recovery objective.
- [ ] **INV-71-C051-IMP-05** Review the matrix after architecture or dependency changes and block release when a new critical failure has no defined handling.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C051-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C051-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C051-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C051-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C051-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C051-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C051-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C051-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C051-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C051-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C051-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C051-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C051-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C052 — Define automated health and stall detection thresholds for Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No automated health/stall detection thresholds.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C052-IMP-01** Define liveness/readiness/stall signals separately for controller, node agent, Firecracker, guest boot, policy fetch, snapshot restore, network setup, teardown, and telemetry pipeline.
- [ ] **INV-71-C052-IMP-02** Use monotonic deadlines and progress markers rather than only process existence; detect stuck STARTING/STOPPING/VERIFYING_TEARDOWN states.
- [ ] **INV-71-C052-IMP-03** Set thresholds from measured distributions with separate warning and hard-failure bounds; avoid restart loops caused by overly aggressive probes.
- [ ] **INV-71-C052-IMP-04** Define health aggregation so one noncritical dependency degrades readiness without masking a security-critical failure.
- [ ] **INV-71-C052-IMP-05** Test hangs, deadlocks, blocked I/O, lost child process, frozen guest, stalled network setup, and telemetry backpressure.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C052-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C052-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C052-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C052-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C052-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C052-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C052-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C052-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C052-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C052-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C052-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C052-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C052-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C053 — Implement bounded retry with backoff and jitter only where operations are safe to retry.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No bounded retry/backoff/jitter implementation or retry-safety classification.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C053-IMP-01** Classify every operation as non-retryable, idempotent retryable, or retryable only with idempotency/compensation safeguards.
- [ ] **INV-71-C053-IMP-02** Implement bounded exponential backoff with full/equal jitter, maximum attempts, maximum elapsed time, and caller deadline propagation.
- [ ] **INV-71-C053-IMP-03** Use idempotency keys/operation IDs for session creation, teardown, policy application, and artifact fetch side effects; persist dedupe state across controller restart as required.
- [ ] **INV-71-C053-IMP-04** Do not retry authentication/authorization/policy denials or integrity failures as transient infrastructure errors.
- [ ] **INV-71-C053-IMP-05** Test retry storms, duplicate responses, timeout-after-commit, late success, controller restart, and dependency flapping.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C053-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C053-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C053-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C053-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C053-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C053-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C053-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C053-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C053-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C053-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C053-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C053-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C053-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C054 — Implement admission control, load shedding, or circuit breaking to prevent Heavy agent sandbox failure cascades.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No admission control, load shedding, or circuit breaker.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C054-IMP-01** Define admission inputs: free memory/vCPU, cgroup headroom, KVM slots, file descriptors, network capacity, snapshot/image cache pressure, disk IOPS, and control-plane queue depth.
- [ ] **INV-71-C054-IMP-02** Reserve emergency/management capacity so overload cannot prevent teardown, quarantine, or operator recovery actions.
- [ ] **INV-71-C054-IMP-03** Implement tenant-aware admission and load shedding before host saturation; reject new work rather than violating isolation/resource ceilings.
- [ ] **INV-71-C054-IMP-04** Add circuit breakers around failing dependencies with bounded half-open probing and no security bypass during open state.
- [ ] **INV-71-C054-IMP-05** Load-test overload and recovery to verify queue bounds, fairness, stable rejection codes, and absence of retry amplification.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C054-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C054-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C054-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C054-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C054-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C054-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C054-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C054-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C054-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C054-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C054-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C054-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C054-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C055 — Define failover behavior without violating isolation, residency, or consistency requirements.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No failover design constrained by isolation/residency/consistency.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C055-IMP-01** Define what can fail over: stateless controller functions, policy distribution, artifact registry, audit sinks, schedulers, and site control plane; identify session-local state that cannot be transparently moved.
- [ ] **INV-71-C055-IMP-02** Constrain placement/failover by tenant residency, site affinity, hardware trust, image availability, and snapshot portability.
- [ ] **INV-71-C055-IMP-03** Define authoritative ownership transfer with fencing tokens/leases so two controllers cannot operate the same session.
- [ ] **INV-71-C055-IMP-04** For stateful recovery, specify whether sessions restart from clean base, resume from approved snapshot, or fail terminally; never migrate unverified residual state by default.
- [ ] **INV-71-C055-IMP-05** Test region/site/controller failover with partitions and stale peers while verifying isolation and residency invariants.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C055-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C055-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C055-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C055-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C055-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C055-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C055-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C055-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C055-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C055-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C055-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C055-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C055-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C056 — Provide degraded operation when noncritical dependencies are unavailable.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No explicit degraded-mode behavior for noncritical dependency loss.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C056-IMP-01** Classify dependencies as security-critical versus noncritical and define an explicit degraded capability set for each noncritical outage.
- [ ] **INV-71-C056-IMP-02** Allow only operations whose required trust/policy/artifact state is locally verifiable; do not turn degraded mode into implicit bypass.
- [ ] **INV-71-C056-IMP-03** Examples to define explicitly: telemetry backend unavailable, dashboard unavailable, secondary registry unavailable, nonessential metadata service unavailable.
- [ ] **INV-71-C056-IMP-04** Expose DEGRADED health with reason, start time, affected capability, and operator action; cap duration where buffered state can grow.
- [ ] **INV-71-C056-IMP-05** Test entry, sustained operation, and exit from each degraded mode including backlog flush and state reconciliation.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C056-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C056-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C056-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C056-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C056-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C056-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C056-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C056-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C056-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C056-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C056-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C056-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C056-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C057 — Define crash-consistency, restart, resume, or replay semantics for mutable Heavy agent sandbox state.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Clean re-instantiation and closed-state semantics exist; crash consistency, restart/resume, replay, and mutable production state semantics are absent.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C057-IMP-01** Define persistence boundaries for controller operation records, session ownership, policy/config generations, teardown evidence, and any resumable guest state.
- [ ] **INV-71-C057-IMP-02** Specify write ordering/fsync/transaction requirements so crashes cannot report READY or VERIFIED before durable prerequisites complete.
- [ ] **INV-71-C057-IMP-03** On restart, reconcile actual Firecracker processes, cgroups, TAP devices, block overlays, and control-plane records rather than assuming database state is authoritative.
- [ ] **INV-71-C057-IMP-04** Define replay behavior for in-flight idempotent operations and orphan cleanup for indeterminate sessions.
- [ ] **INV-71-C057-IMP-05** Crash-inject at every state transition and storage commit point and verify recovery reaches a safe deterministic state.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C057-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C057-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C057-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C057-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C057-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C057-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C057-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C057-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C057-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C057-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C057-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C057-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C057-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C058 — Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No split-brain, duplicate ownership, stale-controller, or duplicate-execution protection.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C058-IMP-01** Use leases/epochs/fencing tokens for session ownership and reject commands from stale controller epochs at node agents.
- [ ] **INV-71-C058-IMP-02** Persist operation IDs and deduplicate mutating commands so at-least-once delivery cannot create duplicate microVMs or duplicate teardown side effects.
- [ ] **INV-71-C058-IMP-03** Detect duplicate node identity and split control-plane membership; quarantine ambiguous ownership instead of picking arbitrarily.
- [ ] **INV-71-C058-IMP-04** Ensure stale policy/config writers cannot overwrite a newer committed generation.
- [ ] **INV-71-C058-IMP-05** Partition-test controller replicas and delayed messages, then verify exactly one active owner can manipulate each session boundary.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C058-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C058-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C058-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C058-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C058-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C058-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C058-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C058-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C058-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C058-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C058-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C058-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C058-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C059 — Provide quarantine, freeze, disable, or isolation controls for unsafe Heavy agent sandbox behavior.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Teardown closes a reference session; operator quarantine/freeze/disable controls for production workloads are absent.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C059-IMP-01** Implement emergency controls to deny new sessions globally/site/tenant/workload, quarantine a node, freeze scheduling, revoke egress, isolate a microVM network, and force/controlled teardown.
- [ ] **INV-71-C059-IMP-02** Separate safe freeze from destructive terminate; document when each is appropriate for forensics versus containment.
- [ ] **INV-71-C059-IMP-03** Require strong authorization, explicit reason, correlation/incident ID, and tamper-evident audit for emergency actions.
- [ ] **INV-71-C059-IMP-04** Ensure emergency controls remain operable under overload and partial control-plane failure using reserved capacity or local node command paths.
- [ ] **INV-71-C059-IMP-05** Drill compromised-guest, compromised-node, malicious-image, and bad-rollout containment and measure time to stop new exposure.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C059-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C059-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C059-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C059-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C059-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C059-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C059-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C059-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C059-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C059-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C059-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C059-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C059-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C060 — Run fault-injection tests proving Heavy agent sandbox recovery against documented objectives.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No fault-injection recovery test suite.  
**Suggested evidence locations:** `docs/failure-matrix.md`, `tests/fault/`, `runbooks/recovery/`

#### Targeted engineering checklist

- [ ] **INV-71-C060-IMP-01** Build an automated fault-injection harness capable of killing Firecracker/node-agent/controller processes, blocking network paths, corrupting caches, delaying dependencies, exhausting disk/memory, and forcing timeouts.
- [ ] **INV-71-C060-IMP-02** Tie each injected fault to the C051 failure matrix and a concrete detection/recovery objective.
- [ ] **INV-71-C060-IMP-03** Verify recovery does not weaken egress/isolation/authentication and does not leak session state to replacement workloads.
- [ ] **INV-71-C060-IMP-04** Run single faults and selected correlated faults during steady load and rollout/rollback transitions.
- [ ] **INV-71-C060-IMP-05** Persist experiment parameters, random seed where applicable, component versions, traces/logs/metrics, and pass/fail evidence for release certification.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C060-DES-01** Define detection signal, timeout, blast radius, automatic action, operator action, and final state for the failure mode.
- [ ] **INV-71-C060-DES-02** Use bounded retries/idempotency/fencing where relevant and prohibit recovery paths that weaken isolation or trust checks.
- [ ] **INV-71-C060-DES-03** Instrument recovery state and expose progress so operators can distinguish slow recovery from a stalled system.
- [ ] **INV-71-C060-DES-04** Fault-inject the condition under load and verify recovery against an explicit time/data/isolation objective.

#### Verification and evidence

- [ ] **INV-71-C060-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C060-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C060-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C060-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C060-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C060-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C060-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C060-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C060-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Performance & Resource Efficiency

### INV-71-C061 — Establish reproducible baselines for Heavy agent sandbox latency, throughput, startup, CPU, memory, storage, network, and power overhead.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No reproducible latency/throughput/startup/CPU/memory/storage/network/power baselines.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C061-IMP-01** Create a reproducible benchmark harness with fixed host hardware/CPU governor/kernel/microcode, artifact versions, dataset/workload, network conditions, and measurement methodology.
- [ ] **INV-71-C061-IMP-02** Measure cold create, warm-snapshot restore, guest-ready, first-exec, steady execution, egress path, and teardown latency plus throughput and concurrency.
- [ ] **INV-71-C061-IMP-03** Record host and per-session CPU, RSS/PSS, page faults, block bytes/IOPS/latency, network bytes/pps/connections, image/snapshot cache, and control-plane overhead.
- [ ] **INV-71-C061-IMP-04** Measure density and overhead at increasing concurrent-session counts and include idle/steady/burst cases.
- [ ] **INV-71-C061-IMP-05** For edge profiles, include power draw and thermal throttling; publish raw data, environment fingerprint, confidence/variance, and baseline release digest.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C061-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C061-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C061-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C061-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C061-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C061-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C061-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C061-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C061-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C061-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C061-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C061-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C061-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C062 — Define p50, p95, p99, and worst-case performance thresholds for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`  
**Observed gap:** A p99 startup target is present; p50/p95/worst-case targets across CPU/memory/storage/network are absent.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C062-IMP-01** Define p50/p95/p99 and hard maximum or timeout thresholds for create-to-ready, restore, network setup, policy application, teardown, and selected control-plane calls.
- [ ] **INV-71-C062-IMP-02** Set CPU, memory, storage latency/throughput, network, and host-density ceilings/floors alongside latency targets.
- [ ] **INV-71-C062-IMP-03** Specify separate thresholds for cold cache, warm cache, steady load, and supported edge hardware classes where behavior differs materially.
- [ ] **INV-71-C062-IMP-04** Define sample-size, warmup, outlier, confidence, and regression-comparison rules to prevent noisy measurements from passing/failing arbitrarily.
- [ ] **INV-71-C062-IMP-05** Encode thresholds in the release benchmark gate instead of relying on manually read dashboards.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C062-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C062-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C062-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C062-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C062-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C062-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C062-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C062-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C062-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C062-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C062-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C062-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C062-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C063 — Measure Heavy agent sandbox under steady load, burst load, overload, scale-out, scale-in, and recovery.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No steady/burst/overload/scale-out/scale-in/recovery performance test suite.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C063-IMP-01** Define workload profiles for steady utilization, sudden burst, sustained overload, rapid scale-out, scale-in/teardown storm, dependency recovery, and cache-cold restart.
- [ ] **INV-71-C063-IMP-02** Measure latency distributions, error/rejection rates, fairness, host saturation, queue depth, resource leakage, and recovery time through each phase.
- [ ] **INV-71-C063-IMP-03** Include multi-tenant mixes with different resource shapes so aggregate averages cannot hide starvation.
- [ ] **INV-71-C063-IMP-04** Run transitions repeatedly to detect hysteresis, leaked cgroups/TAP devices/processes, degraded cache behavior, or control-plane backlog.
- [ ] **INV-71-C063-IMP-05** Compare every release to the approved baseline using automated regression thresholds.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C063-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C063-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C063-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C063-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C063-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C063-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C063-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C063-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C063-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C063-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C063-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C063-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C063-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C064 — Measure per-workload and per-tenant overhead introduced by Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No per-workload/per-tenant overhead measurements.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C064-IMP-01** Attribute host overhead per session/tenant for VMM processes, jailer helpers, page cache, writable overlays, networking, telemetry, and control-plane bookkeeping.
- [ ] **INV-71-C064-IMP-02** Measure fixed per-session cost separately from workload-proportional cost and from shared fleet services.
- [ ] **INV-71-C064-IMP-03** Quantify noisy-neighbor impact by running victim/aggressor tenant pairs across CPU, memory, I/O, network, and session-create storms.
- [ ] **INV-71-C064-IMP-04** Publish tenant billing/capacity accounting semantics if overhead contributes to quotas or cost allocation.
- [ ] **INV-71-C064-IMP-05** Set maximum acceptable isolation overhead and detect releases that increase it beyond tolerance.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C064-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C064-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C064-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C064-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C064-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C064-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C064-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C064-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C064-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C064-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C064-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C064-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C064-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C065 — Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No profiling evidence for copies, serialization, context switches, hops, duplicated images, or duplicated state.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C065-IMP-01** Profile end-to-end create/start/exec/teardown paths with CPU profiles, syscall counts, context switches, allocation profiles, I/O traces, and network hop timing.
- [ ] **INV-71-C065-IMP-02** Count serialized/deserialized copies for control requests, audit events, policy bundles, and any guest-host data path; identify avoidable transcodes/copies.
- [ ] **INV-71-C065-IMP-03** Measure duplicated image/rootfs/snapshot storage and page-cache duplication across sessions/nodes.
- [ ] **INV-71-C065-IMP-04** Identify lock contention and scheduler wakeups in high-concurrency control-plane/node-agent paths.
- [ ] **INV-71-C065-IMP-05** Turn findings into tracked optimization items with before/after measurements and a requirement that security semantics remain unchanged.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C065-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C065-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C065-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C065-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C065-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C065-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C065-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C065-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C065-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C065-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C065-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C065-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C065-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C066 — Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No measured/justified locality, caching, batching, zero-copy, direct-composition, or kernel-bypass optimization plan.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C066-IMP-01** Prefer local verified snapshot/image caches while retaining digest/signature validation and explicit cache freshness/revocation behavior.
- [ ] **INV-71-C066-IMP-02** Batch only operations whose ordering/idempotency semantics allow batching; never batch security decisions in a way that obscures per-session auditability.
- [ ] **INV-71-C066-IMP-03** Evaluate reflink/copy-on-write, shared read-only pages, direct I/O, zero-copy/vsock approaches, or reduced network hops where supported and measured beneficial.
- [ ] **INV-71-C066-IMP-04** Use topology-aware scheduling to improve locality without violating tenant separation, residency, or side-channel policy.
- [ ] **INV-71-C066-IMP-05** For every optimization, record baseline, expected gain, new failure/security risks, rollback switch, and measured production-equivalent result.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C066-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C066-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C066-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C066-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C066-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C066-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C066-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C066-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C066-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C066-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C066-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C066-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C066-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C067 — Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Disk/file/history growth is bounded; production memory, queues, buffers, concurrency, process count, and resource fan-out are not comprehensively bounded.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C067-IMP-01** Set explicit upper bounds for controller/node-agent memory, per-session metadata, audit/log buffers, telemetry queues, policy cache, image cache index, connection pools, and concurrent goroutine/thread/task counts.
- [ ] **INV-71-C067-IMP-02** Use bounded queues with backpressure/drop policy by data criticality; security audit loss must not be silently accepted.
- [ ] **INV-71-C067-IMP-03** Limit fan-out for artifact fetch, policy refresh, health checks, and teardown to prevent synchronized storms.
- [ ] **INV-71-C067-IMP-04** Instrument high-water marks and growth rate and trigger protective admission/shedding before OOM or descriptor exhaustion.
- [ ] **INV-71-C067-IMP-05** Run long-duration and adversarial amplification tests proving memory/queue/resource usage converges rather than grows without bound.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C067-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C067-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C067-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C067-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C067-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C067-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C067-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C067-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C067-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C067-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C067-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C067-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C067-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C068 — Measure power and thermal impact on constrained edge nodes where relevant.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No power/thermal measurements for constrained edge nodes.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C068-IMP-01** Select representative constrained edge hardware and record PSU/battery input power, CPU package power where available, temperatures, fan state, frequency, and throttling.
- [ ] **INV-71-C068-IMP-02** Measure idle runtime cost, session startup burst, steady workload, concurrent-session density, image/snapshot transfer, and teardown storms.
- [ ] **INV-71-C068-IMP-03** Define thermal/power operating envelopes and derating rules that feed admission control before hardware throttling causes SLO collapse.
- [ ] **INV-71-C068-IMP-04** Assess whether optimization choices such as polling, busy loops, compression, encryption, or cache warming materially change power/thermal behavior.
- [ ] **INV-71-C068-IMP-05** Publish repeatable test setup and pass criteria for each supported edge class.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C068-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C068-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C068-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C068-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C068-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C068-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C068-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C068-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C068-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C068-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C068-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C068-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C068-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C069 — Define capacity models and saturation signals that predict when Heavy agent sandbox needs more resources.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No capacity model or saturation signals tied to scaling decisions.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C069-IMP-01** Build a capacity model connecting host cores, memory, KVM/VMM overhead, block/network throughput, image/snapshot cache, file descriptors, and session shape to safe concurrency.
- [ ] **INV-71-C069-IMP-02** Identify leading saturation indicators rather than only terminal failures: memory pressure/PSI, CPU steal/run queue, I/O latency, queue depth, connection counts, cache miss/fetch rate, and create latency.
- [ ] **INV-71-C069-IMP-03** Define headroom/reservation policy for teardown, quarantine, system daemons, and failover.
- [ ] **INV-71-C069-IMP-04** Validate the model against measured scale tests and recalibrate when workload mix or runtime versions change.
- [ ] **INV-71-C069-IMP-05** Feed capacity signals into scheduler/admission decisions and alert before saturation breaches production SLOs.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C069-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C069-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C069-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C069-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C069-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C069-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C069-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C069-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C069-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C069-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C069-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C069-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C069-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C070 — Block releases that regress approved Heavy agent sandbox startup, density, throughput, or tail-latency thresholds.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No automated release gate for startup/density/throughput/tail-latency regressions.  
**Suggested evidence locations:** `benchmarks/`, `evidence/performance/`, `capacity/`

#### Targeted engineering checklist

- [ ] **INV-71-C070-IMP-01** Create a CI/performance gate that compares candidate startup, density, throughput, resource overhead, and tail latency against an approved baseline on controlled hardware.
- [ ] **INV-71-C070-IMP-02** Set absolute thresholds plus allowed regression percentages and minimum sample sizes/confidence rules.
- [ ] **INV-71-C070-IMP-03** Separate environment noise from real regression using repeated runs and hardware fingerprint checks; reject invalid benchmark environments.
- [ ] **INV-71-C070-IMP-04** Require explicit reviewed waiver with expiry for any accepted regression and preserve the benchmark evidence with the release artifact.
- [ ] **INV-71-C070-IMP-05** Add rollback criteria when production canary measurements exceed the same guardrails.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C070-DES-01** Define a reproducible measurement environment, workload profile, raw metrics, aggregation method, and acceptance threshold.
- [ ] **INV-71-C070-DES-02** Measure p50/p95/p99 plus worst-case/timeout behavior and resource overhead, not averages alone.
- [ ] **INV-71-C070-DES-03** Test multi-tenant contention and overload so performance improvements cannot mask fairness or isolation regressions.
- [ ] **INV-71-C070-DES-04** Encode the approved threshold into an automated regression gate with retained raw evidence.

#### Verification and evidence

- [ ] **INV-71-C070-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C070-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C070-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C070-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C070-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C070-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C070-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C070-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C070-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Observability & Explainability

### INV-71-C071 — Expose Heavy agent sandbox health, readiness, version, configuration, dependency status, and active capability set.

**Audit status:** `PARTIAL`  
**Existing evidence:** `__init__.py`, `sandbox.py`  
**Observed gap:** Version and session state exist locally; there is no production health/readiness/config/dependency/capability status endpoint.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C071-IMP-01** Expose authenticated health/readiness/status endpoints containing implementation version, API/schema versions, effective configuration digest, artifact set digest, node identity, and active capability set.
- [ ] **INV-71-C071-IMP-02** Report dependency states separately for identity, policy, artifact store/cache, network enforcement, snapshot store, telemetry sinks, and KVM/runtime.
- [ ] **INV-71-C071-IMP-03** Expose current controller epoch/session counts/capacity headroom without leaking tenant-sensitive data to unauthorized callers.
- [ ] **INV-71-C071-IMP-04** Differentiate liveness, readiness for new sessions, degraded service, and quarantined/unsafe states.
- [ ] **INV-71-C071-IMP-05** Contract-test status schema and verify every readiness transition corresponds to real operational prerequisites.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C071-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C071-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C071-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C071-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C071-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C071-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C071-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C071-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C071-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C071-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C071-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C071-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C071-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C072 — Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`  
**Observed gap:** Metric names are declared, but no structured metrics emitter/exporter is implemented.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C072-IMP-01** Implement structured metrics for request/session rates, errors by stable reason code, latency histograms, active/queued sessions, admission rejections, teardown outcomes, and dependency state.
- [ ] **INV-71-C072-IMP-02** Export resource metrics for host and VMM CPU/memory, cgroups, block I/O, network, PID/FD use, caches, queues, and audit buffering.
- [ ] **INV-71-C072-IMP-03** Use bounded-cardinality labels; do not put raw session IDs, hostnames, URLs, secrets, or unbounded tenant-controlled strings in metric labels.
- [ ] **INV-71-C072-IMP-04** Define units, histogram buckets, reset semantics, monotonicity, aggregation, and SLI formulas in a metric catalog.
- [ ] **INV-71-C072-IMP-05** Load-test the exporter and verify telemetry collection cannot materially perturb sandbox isolation or performance.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C072-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C072-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C072-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C072-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C072-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C072-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C072-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C072-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C072-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C072-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C072-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C072-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C072-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C073 — Emit structured logs with stable node, tenant, workload, component, and operation identifiers.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Structured reference audit events exist but lack production node/tenant/workload correlation and durable log export.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C073-IMP-01** Emit structured logs with stable node ID, tenant-safe tenant/workload IDs, session/operation/correlation IDs, component, state transition, reason code, config/policy/artifact version, and severity.
- [ ] **INV-71-C073-IMP-02** Define a canonical event taxonomy so operators can distinguish security rejection, dependency failure, resource rejection, guest failure, and internal defect.
- [ ] **INV-71-C073-IMP-03** Apply field-level redaction and allowlists; never log credentials, tokens, raw secret environment, arbitrary guest file contents, or cross-tenant payloads.
- [ ] **INV-71-C073-IMP-04** Deliver logs durably or spool with bounded storage and explicit loss signaling; include clock-quality metadata where ordering matters.
- [ ] **INV-71-C073-IMP-05** Test correlation across controller→node→Firecracker lifecycle and ensure one incident can be reconstructed without grepping free-form text.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C073-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C073-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C073-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C073-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C073-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C073-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C073-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C073-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C073-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C073-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C073-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C073-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C073-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C074 — Propagate trace context across all relevant Heavy agent sandbox boundaries.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No distributed trace-context propagation.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C074-IMP-01** Adopt a standard trace-context format and propagate it across public API, controller, scheduler, node agent, artifact/policy calls, network decision service, and telemetry export.
- [ ] **INV-71-C074-IMP-02** Create spans for create validation, admission, artifact resolution, snapshot restore, network/cgroup setup, guest boot, teardown, and cleanup verification.
- [ ] **INV-71-C074-IMP-03** Do not inject tenant trace headers into privileged host components without validation; separate untrusted guest tracing from control-plane tracing where needed.
- [ ] **INV-71-C074-IMP-04** Apply sampling rules that preserve errors/security-critical flows while bounding high-cardinality cost.
- [ ] **INV-71-C074-IMP-05** Integration-test context continuity through retries, async queues, process boundaries, and mixed-version peers.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C074-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C074-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C074-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C074-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C074-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C074-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C074-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C074-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C074-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C074-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C074-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C074-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C074-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C075 — Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No safe high-cardinality diagnostic mechanism with tenant/secret redaction controls.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C075-IMP-01** Define an authenticated privileged diagnostic surface for per-session/node detail that is intentionally not exported as high-cardinality metrics.
- [ ] **INV-71-C075-IMP-02** Use field-level authorization and redaction for tenant identifiers, destination names, paths, environment metadata, and guest-originated strings.
- [ ] **INV-71-C075-IMP-03** Bound query ranges, result sizes, concurrency, and retention to prevent the diagnostic plane from becoming a DoS or data-exfiltration channel.
- [ ] **INV-71-C075-IMP-04** Tag diagnostic data by classification and automatically remove secrets/tokens using structured-source allowlists rather than regex-only redaction.
- [ ] **INV-71-C075-IMP-05** Security-test cross-tenant queries, enumeration, injection, oversized filters, and operator privilege downgrade.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C075-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C075-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C075-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C075-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C075-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C075-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C075-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C075-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C075-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C075-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C075-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C075-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C075-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C076 — Record the reason for every automated decision made by Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `sandbox.py`  
**Observed gap:** Reference decisions carry reason text for several operations; not every automated production decision is covered.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C076-IMP-01** For every automated allow/deny/place/retry/admit/shed/quarantine/rollback/teardown decision, record a stable reason code plus human-readable explanation.
- [ ] **INV-71-C076-IMP-02** Capture the decision inputs by digest/reference: policy version, config version, capacity snapshot, dependency state, artifact version, identity/claims, and controller epoch.
- [ ] **INV-71-C076-IMP-03** Ensure reason generation is deterministic and cannot be supplied/forged by the untrusted guest.
- [ ] **INV-71-C076-IMP-04** Include both selected outcome and rejected alternatives where useful for operator diagnosis, without exposing other tenants.
- [ ] **INV-71-C076-IMP-05** Add tests asserting every branch of security- and availability-sensitive decision logic emits an explainable reason.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C076-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C076-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C076-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C076-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C076-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C076-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C076-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C076-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C076-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C076-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C076-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C076-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C076-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C077 — Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No operator explain view tying decisions to policy/input/topology/constraints.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C077-IMP-01** Build an operator explain view/CLI that reconstructs a session or failed request from lifecycle events, policy/config versions, artifact lineage, topology/node, capacity, and dependency status.
- [ ] **INV-71-C077-IMP-02** Show which rule/constraint caused allow, deny, placement, retry, degradation, or quarantine and display the exact version/digest evaluated.
- [ ] **INV-71-C077-IMP-03** Link to relevant logs/traces/audit events using correlation IDs while enforcing tenant/operator authorization.
- [ ] **INV-71-C077-IMP-04** Support point-in-time explanation so later policy changes do not rewrite the explanation of an earlier decision.
- [ ] **INV-71-C077-IMP-05** Validate the view against known scenarios and require operators to resolve injected incidents using only the supported explain path.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C077-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C077-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C077-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C077-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C077-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C077-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C077-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C077-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C077-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C077-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C077-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C077-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C077-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C078 — Correlate Heavy agent sandbox events with application release lineage and the live infrastructure graph.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No correlation with application release lineage or live infrastructure graph.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C078-IMP-01** Attach application/workload release identifiers and immutable image/code digests to session create requests and carry them through lifecycle telemetry.
- [ ] **INV-71-C078-IMP-02** Record infrastructure lineage: node image/kernel/microcode, Firecracker/jailer, guest kernel/rootfs, snapshot digest, policy/config generation, and network enforcement version.
- [ ] **INV-71-C078-IMP-03** Integrate with the infrastructure graph/CMDB so events can be queried by host, rack/site, network zone, artifact, rollout cohort, and dependency.
- [ ] **INV-71-C078-IMP-04** Preserve historical topology references so past incidents remain explainable after resources move or are deleted.
- [ ] **INV-71-C078-IMP-05** Test correlation from an application release to all affected sessions/nodes and from a bad node/runtime artifact back to impacted workloads.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C078-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C078-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C078-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C078-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C078-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C078-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C078-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C078-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C078-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C078-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C078-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C078-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C078-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C079 — Define telemetry retention, sampling, privacy, and export policy.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No telemetry retention, sampling, privacy, or export policy.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C079-IMP-01** Define retention periods by telemetry class: security audit, operational logs, traces, metrics, benchmark evidence, and high-cardinality diagnostics.
- [ ] **INV-71-C079-IMP-02** Define sampling policies and explicit unsampled classes such as critical security/audit events; document acceptable telemetry loss and backpressure behavior.
- [ ] **INV-71-C079-IMP-03** Classify fields for privacy/residency and restrict export destinations, cross-region replication, and operator access accordingly.
- [ ] **INV-71-C079-IMP-04** Specify encryption, deletion, legal hold, tenant deletion, and data minimization requirements for retained telemetry.
- [ ] **INV-71-C079-IMP-05** Audit exporters and retention jobs regularly and test that expired data is deleted while required security evidence remains verifiable.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C079-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C079-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C079-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C079-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C079-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C079-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C079-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C079-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C079-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C079-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C079-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C079-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C079-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C080 — Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No dashboards/alerts separating load, degradation, policy rejection, dependency failure, attack, and defects.  
**Suggested evidence locations:** `observability/`, `dashboards/`, `alerts/`, `docs/telemetry/`

#### Targeted engineering checklist

- [ ] **INV-71-C080-IMP-01** Create dashboards separating normal load/saturation, degraded dependency, policy/security rejection, malicious/attack indicators, guest-caused failure, and suspected software defect.
- [ ] **INV-71-C080-IMP-02** Alert on zero-budget isolation/egress violations, failed artifact verification, unauthorized privileged actions, teardown verification failure, and audit-chain/sink integrity failures with highest urgency.
- [ ] **INV-71-C080-IMP-03** Define symptom plus cause-oriented alerts for create latency, admission rejection, crash loops, stale policy, identity/key outages, queue growth, and node quarantine.
- [ ] **INV-71-C080-IMP-04** Attach runbook links, ownership, severity, suppression/deduplication, and paging routes to every actionable alert.
- [ ] **INV-71-C080-IMP-05** Exercise dashboards/alerts with synthetic and fault-injected incidents and measure detection plus operator diagnosis time.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C080-DES-01** Define a stable schema/catalog for emitted telemetry, reason codes, identifiers, units, cardinality, and redaction rules.
- [ ] **INV-71-C080-DES-02** Correlate controller, node, runtime, network, artifact, and workload events with a common operation/session lineage.
- [ ] **INV-71-C080-DES-03** Bound telemetry CPU/memory/storage/network cost and define behavior when sinks are slow/unavailable.
- [ ] **INV-71-C080-DES-04** Create operator-facing queries/dashboards plus synthetic tests proving the signal is actionable and privacy-safe.

#### Verification and evidence

- [ ] **INV-71-C080-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C080-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C080-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C080-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C080-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C080-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C080-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C080-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C080-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Testing & Certification

### INV-71-C082 — Create contract tests for every public Heavy agent sandbox interface.

**Audit status:** `PARTIAL`  
**Existing evidence:** `schemas/`, `tests/test_sandbox.py`  
**Observed gap:** Record schemas and unit behavior tests exist; transport/API contract tests for every public interface are absent.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C082-IMP-01** Create contract tests for every public API/event/schema including happy path, all required fields, bounds, enum evolution, unknown fields, invalid types, malformed encoding, and redaction behavior.
- [ ] **INV-71-C082-IMP-02** Test semantic behavior as well as schema shape: idempotency, deadlines, cancellation, authorization, state-transition rules, and stable error codes.
- [ ] **INV-71-C082-IMP-03** Run the same contract suite against client/server implementations for every supported version pair.
- [ ] **INV-71-C082-IMP-04** Include golden wire fixtures and canonical signing/hashing vectors where byte representation matters.
- [ ] **INV-71-C082-IMP-05** Fail release when an interface change lacks updated compatibility fixtures and migration notes.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C082-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C082-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C082-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C082-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C082-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C082-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C082-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C082-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C082-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C082-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C082-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C082-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C082-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C083 — Create integration tests with every supported adjacent layer and execution tier.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No production integration tests across every supported adjacent layer/execution tier.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C083-IMP-01** Run production-like integration tests with the real scheduler/workload layer, Firecracker runtime/jailer, snapshot subsystem, network enforcement, identity/policy services, artifact store, and observability sinks.
- [ ] **INV-71-C083-IMP-02** Exercise full lifecycle under success, dependency timeout, partial outage, malformed input, revoked identity, tampered artifact, capacity rejection, guest crash, and teardown failure.
- [ ] **INV-71-C083-IMP-03** Validate host resources before and after each test: Firecracker processes, cgroups, netns/TAP devices, mounts, overlay files, sockets, and descriptors must return to baseline.
- [ ] **INV-71-C083-IMP-04** Test each supported deployment tier/profile rather than assuming cloud behavior represents edge/datacenter behavior.
- [ ] **INV-71-C083-IMP-05** Collect version/digest and machine-readable evidence sufficient to reproduce any failed integration run.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C083-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C083-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C083-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C083-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C083-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C083-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C083-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C083-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C083-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C083-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C083-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C083-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C083-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C084 — Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No compatibility test matrix across architectures, hypervisors, runtimes, providers, or protocol versions.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C084-IMP-01** Create a compatibility matrix for supported CPU architectures/vendors, host kernel lines, Firecracker/jailer versions, guest kernels/rootfs generations, snapshot formats, node-agent versions, API/schema versions, and provider/environment profiles.
- [ ] **INV-71-C084-IMP-02** Mark combinations as supported, unsupported, upgrade-only, downgrade-incompatible, or requiring snapshot rebuild.
- [ ] **INV-71-C084-IMP-03** Run representative create/restore/network/teardown/security tests for every supported combination and especially rolling-upgrade skew pairs.
- [ ] **INV-71-C084-IMP-04** Detect CPU-feature/snapshot portability assumptions explicitly; do not claim migration across hardware classes without measured proof.
- [ ] **INV-71-C084-IMP-05** Version the matrix and block deployment of untested/unapproved combinations.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C084-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C084-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C084-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C084-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C084-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C084-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C084-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C084-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C084-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C084-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C084-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C084-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C084-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C085 — Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No fuzzing for schemas, parsers, protocol handlers, control-plane inputs, or other untrusted inputs.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C085-IMP-01** Fuzz JSON/schema/API decoders, policy/config parsers, image/snapshot metadata parsers, hostname/IP normalization, error/detail parsers, and any vsock/RPC/HTTP/gRPC boundary that accepts untrusted bytes.
- [ ] **INV-71-C085-IMP-02** Use coverage-guided fuzzing where native components permit it and property-based generation for stateful lifecycle/protocol sequences.
- [ ] **INV-71-C085-IMP-03** Seed corpora with all conformance fixtures, historical bugs, boundary sizes, Unicode/path edge cases, DNS/IP forms, and malformed length/encoding inputs.
- [ ] **INV-71-C085-IMP-04** Run fuzzers under sanitizers/UB checks for native code and with strict resource/time limits; retain minimized crash inputs as regression tests.
- [ ] **INV-71-C085-IMP-05** Define release fuzzing duration/coverage expectations and triage ownership for crashes, hangs, assertion failures, and excessive resource use.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C085-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C085-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C085-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C085-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C085-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C085-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C085-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C085-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C085-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C085-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C085-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C085-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C085-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C086 — Create concurrency and race-condition tests for shared/distributed Heavy agent sandbox state.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No concurrency/race-condition tests for shared/distributed production state.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C086-IMP-01** Create concurrent tests for duplicate create/stop/teardown, simultaneous policy/config changes, controller failover, lease renewal, quota updates, and node reconciliation.
- [ ] **INV-71-C086-IMP-02** Use race detectors/thread sanitizers where implementation language supports them and deterministic schedulers/model tests for critical state machines where possible.
- [ ] **INV-71-C086-IMP-03** Stress shared caches, maps, queues, audit sequence generation, idempotency stores, and session ownership under thousands of interleavings.
- [ ] **INV-71-C086-IMP-04** Verify invariants: one active owner, at most one microVM per session ID, monotonic generation, no negative quota/accounting, and exactly-once final disposition semantics where specified.
- [ ] **INV-71-C086-IMP-05** Promote every discovered race/deadlock to a minimized repeatable regression test.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C086-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C086-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C086-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C086-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C086-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C086-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C086-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C086-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C086-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C086-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C086-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C086-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C086-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C087 — Create security tests derived directly from the Heavy agent sandbox threat model.

**Audit status:** `PARTIAL`  
**Existing evidence:** `docs/THREAT_MODEL.md`, `tests/test_sandbox.py`  
**Observed gap:** Some tests derive from threats, but the threat-model test suite is incomplete and does not exercise a real isolation boundary.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C087-IMP-01** Convert every row and residual risk in THREAT_MODEL.md into one or more executable security test IDs with explicit expected control behavior.
- [ ] **INV-71-C087-IMP-02** Run cross-session residue, host escape/privilege, malicious artifact, DNS rebinding/destination, control-plane authz, secret leakage, replay/spoofing, resource exhaustion, and audit tamper scenarios against the real boundary.
- [ ] **INV-71-C087-IMP-03** Include regression tests for relevant Firecracker, guest-kernel, host-kernel, and jailer vulnerabilities affecting supported versions.
- [ ] **INV-71-C087-IMP-04** Perform periodic independent penetration/adversarial review rather than relying only on implementation-team tests.
- [ ] **INV-71-C087-IMP-05** Track threat→control→test→evidence links in the requirements matrix and prevent closure of a threat without demonstrable mitigation or accepted residual-risk record.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C087-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C087-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C087-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C087-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C087-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C087-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C087-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C087-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C087-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C087-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C087-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C087-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C087-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C088 — Create benchmark, soak, burst, and fleet-scale tests appropriate to Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No benchmark, soak, burst, or fleet-scale test harness.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C088-IMP-01** Build benchmark suites for startup/restore/teardown latency, steady throughput, density, control-plane rate, and egress path under representative workloads.
- [ ] **INV-71-C088-IMP-02** Run soak tests long enough to expose descriptor, process, cgroup, namespace, file, memory, queue, and cache leaks across repeated session churn.
- [ ] **INV-71-C088-IMP-03** Run burst tests for session-create and teardown storms plus artifact/policy refresh spikes.
- [ ] **INV-71-C088-IMP-04** Run fleet-scale simulations or test clusters that exercise scheduler/admission/control-plane behavior at expected and beyond-expected node/session counts.
- [ ] **INV-71-C088-IMP-05** Automate result comparison, raw-data retention, host fingerprinting, and regression gating per C061-C070.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C088-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C088-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C088-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C088-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C088-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C088-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C088-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C088-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C088-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C088-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C088-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C088-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C088-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C089 — Create disaster, partition, reconnect, and degraded-control-plane tests.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No disaster/partition/reconnect/degraded-control-plane tests.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C089-IMP-01** Test control-plane partition, site/WAN partition, DNS failure, identity/policy/key outage, artifact-registry loss, telemetry sink loss, and storage/snapshot dependency outage.
- [ ] **INV-71-C089-IMP-02** Test reconnect with queued audit data, stale policy/config, revoked identities, duplicate commands, orphan sessions, and ownership conflicts.
- [ ] **INV-71-C089-IMP-03** Simulate disaster loss of controller/state service/site and execute documented recovery/failover/reconstruction procedures.
- [ ] **INV-71-C089-IMP-04** Verify degraded operation never bypasses artifact verification, authentication, egress enforcement, isolation, or teardown verification.
- [ ] **INV-71-C089-IMP-05** Measure RTO/RPO or equivalent recovery objectives and retain evidence that the achieved result meets the declared target.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C089-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C089-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C089-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C089-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C089-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C089-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C089-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C089-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C089-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C089-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C089-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C089-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C089-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C090 — Require machine-readable acceptance evidence before certifying a Heavy agent sandbox release for production.

**Audit status:** `PARTIAL`  
**Existing evidence:** `AUDIT_AFTER.json`, `REPO_AUDIT_RESULTS.json`  
**Observed gap:** Machine-readable audit evidence exists, but it is not a signed release acceptance/gate artifact for a production implementation.  
**Suggested evidence locations:** `tests/`, `fixtures/`, `evidence/certification/`

#### Targeted engineering checklist

- [ ] **INV-71-C090-IMP-01** Define a signed machine-readable release evidence schema containing source revision, build provenance, SBOM/signatures, dependency versions, configuration schema version, test results, security scans, benchmark gates, and approval identities.
- [ ] **INV-71-C090-IMP-02** Require evidence references by immutable digest and verify signatures before a release can be promoted to production.
- [ ] **INV-71-C090-IMP-03** Encode all 100 INV-71 controls with status and evidence links; do not allow inherited/default framework status to substitute for component-specific proof.
- [ ] **INV-71-C090-IMP-04** Make the gate reproducible: a verifier should be able to re-evaluate evidence offline and obtain the same pass/fail result.
- [ ] **INV-71-C090-IMP-05** Archive the gate result and evidence manifest with the release and reject promotion when required evidence is missing, expired, revoked, or inconsistent.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C090-DES-01** Assign stable test IDs and link each case to one or more requirements/threats/failure modes in the traceability matrix.
- [ ] **INV-71-C090-DES-02** Run tests on production-equivalent versions/hardware and record all artifact/config/environment digests needed for reproduction.
- [ ] **INV-71-C090-DES-03** Include positive, negative, boundary, fault, concurrency, and cleanup verification as applicable; fail on leaked host resources.
- [ ] **INV-71-C090-DES-04** Emit signed or digest-addressed machine-readable results and make the production gate consume them automatically.

#### Verification and evidence

- [ ] **INV-71-C090-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C090-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C090-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C090-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C090-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C090-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C090-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C090-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C090-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Operations, Release & Governance

### INV-71-C091 — Define production SLOs, error budgets, and support commitments for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`  
**Observed gap:** SLOs and error-budget statements exist; support commitments and operational measurement evidence are absent.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C091-IMP-01** Publish production SLIs/SLOs for availability, create-to-ready latency, teardown, audit delivery, dependency health, and capacity rejection, alongside zero-budget security invariants.
- [ ] **INV-71-C091-IMP-02** Define measurement windows, burn-rate/error-budget policy, maintenance handling, support hours, and severity response commitments.
- [ ] **INV-71-C091-IMP-03** Connect SLO violations to rollout pause/rollback and capacity/incident processes rather than treating them as reporting-only metrics.
- [ ] **INV-71-C091-IMP-04** Document service dependencies and which SLOs are end-to-end versus component-local.
- [ ] **INV-71-C091-IMP-05** Validate SLO calculations against production-equivalent telemetry and review targets after meaningful architecture/workload changes.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C091-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C091-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C091-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C091-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C091-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C091-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C091-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C091-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C091-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C091-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C091-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C091-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C091-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C092 — Define canary, staged rollout, rollback, and emergency-disable procedures for Heavy agent sandbox.

**Audit status:** `PARTIAL`  
**Existing evidence:** `README.md`  
**Observed gap:** Rollback/emergency-disable concepts are described; canary/staged rollout implementation and tested rollback are absent.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C092-IMP-01** Define staged rollout cohorts from lab→canary nodes/sites→small production percentage→progressive expansion with explicit observation windows.
- [ ] **INV-71-C092-IMP-02** Specify pre-promotion gates for health, security events, teardown success, startup/tail latency, resource overhead, and compatibility.
- [ ] **INV-71-C092-IMP-03** Automate rollback on critical security/integrity failures and selected SLO regressions; keep an operator emergency-disable path independent of the normal rollout controller.
- [ ] **INV-71-C092-IMP-04** Verify rollback artifacts/config are still approved and compatible before beginning each rollout.
- [ ] **INV-71-C092-IMP-05** Run canary failure and emergency-disable drills and retain time-to-detect/time-to-contain/time-to-rollback evidence.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C092-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C092-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C092-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C092-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C092-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C092-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C092-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C092-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C092-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C092-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C092-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C092-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C092-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C093 — Maintain a supported-version compatibility matrix for Heavy agent sandbox and adjacent dependencies.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No supported-version compatibility matrix for adjacent dependencies.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C093-IMP-01** Maintain a version matrix covering INV-71 node/control-plane, Firecracker/jailer, host kernel, guest kernel/rootfs, snapshot format, schemas/APIs, identity/policy components, and adjacent INV-69/24/26/GAP-09 versions.
- [ ] **INV-71-C093-IMP-02** State minimum/maximum supported versions, rolling-skew allowance, known incompatibilities, required migrations, and end-of-support date.
- [ ] **INV-71-C093-IMP-03** Generate matrix entries from tested release evidence where possible rather than manual assertion.
- [ ] **INV-71-C093-IMP-04** Validate deployment plans against the matrix before rollout and reject unsupported combinations at node/controller startup.
- [ ] **INV-71-C093-IMP-05** Retain historical matrices so an incident can reconstruct what combinations were supported at the time.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C093-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C093-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C093-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C093-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C093-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C093-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C093-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C093-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C093-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C093-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C093-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C093-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C093-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C094 — Define patching, vulnerability response, and end-of-life SLAs for Heavy agent sandbox.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No patching, vulnerability-response, or end-of-life SLA.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C094-IMP-01** Define severity-based patch SLAs for critical/high/medium vulnerabilities affecting Firecracker, host/guest kernels, rootfs packages, node agent, crypto libraries, and build dependencies.
- [ ] **INV-71-C094-IMP-02** Subscribe to relevant security advisories/CVE feeds and map each advisory to the approved-version manifest/SBOM inventory.
- [ ] **INV-71-C094-IMP-03** Create emergency rebuild, signing, canary, rollout, rollback, and node-drain procedures for runtime/kernel/image vulnerabilities.
- [ ] **INV-71-C094-IMP-04** Define supported release lifetime, deprecation notice, end-of-life date, and behavior of nodes/artifacts after EOL.
- [ ] **INV-71-C094-IMP-05** Measure patch latency from disclosure/triage to fleet completion and escalate SLA breaches.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C094-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C094-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C094-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C094-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C094-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C094-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C094-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C094-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C094-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C094-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C094-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C094-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C094-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C095 — Provide backup, restore, migration, or reconstruction procedures for Heavy agent sandbox state where applicable.

**Audit status:** `PARTIAL`  
**Existing evidence:** `contract.py`, `README.md`  
**Observed gap:** Clean-snapshot reconstruction is conceptual; production image/snapshot backup, restore, migration, and validation procedures are absent.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C095-IMP-01** Classify which state is reconstructable from immutable artifacts versus must be backed up: configuration/provenance, control-plane session records, audit evidence, signing metadata, policy bundles, and optional resumable snapshot state.
- [ ] **INV-71-C095-IMP-02** Define backup encryption, retention, geographic/residency rules, immutability, access controls, and restore authorization.
- [ ] **INV-71-C095-IMP-03** For disposable session state, prefer deterministic reconstruction from signed clean artifacts rather than unsafe persistence of writable guest state.
- [ ] **INV-71-C095-IMP-04** Document migration/rebuild procedures for snapshot format or hardware incompatibility and verify restored artifacts before use.
- [ ] **INV-71-C095-IMP-05** Run scheduled restore/reconstruction drills to isolated environments and measure recovery objectives plus completeness/integrity.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C095-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C095-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C095-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C095-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C095-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C095-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C095-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C095-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C095-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C095-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C095-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C095-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C095-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C096 — Create day-0 bootstrap, day-1 deployment, and day-2 operation runbooks.

**Audit status:** `PARTIAL`  
**Existing evidence:** `README.md`  
**Observed gap:** Day-0/day-1/day-2 guidance exists only at a high level and is not an executable production runbook.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C096-IMP-01** Create executable Day-0 runbooks for host qualification, bootstrap, trust setup, artifact prefetch, configuration activation, registration, and production-readiness validation.
- [ ] **INV-71-C096-IMP-02** Create Day-1 deployment runbooks for canary selection, rollout gates, health observation, rollback, and compatibility validation.
- [ ] **INV-71-C096-IMP-03** Create Day-2 runbooks for capacity, node drain, image/runtime patching, policy/config rollout, certificate/key rotation, degraded dependencies, quarantine, cleanup, and evidence verification.
- [ ] **INV-71-C096-IMP-04** For each step define prerequisites, exact commands/API actions, expected outputs, rollback/abort criteria, ownership, and safety warnings.
- [ ] **INV-71-C096-IMP-05** Test runbooks in game days by an operator who did not author them; update any ambiguous or non-reproducible step.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C096-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C096-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C096-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C096-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C096-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C096-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C096-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C096-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C096-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C096-GATE-01** Completion gate: existing partial evidence is extended to the real production path and all remaining semantics/verification gaps are closed with reproducible evidence.
- [ ] **INV-71-C096-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C096-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C096-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C097 — Define incident severity, paging, escalation, containment, and recovery procedures.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No incident severity, paging, escalation, containment, or recovery procedure.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C097-IMP-01** Define incident severities with explicit triggers for isolation breach, forbidden egress, artifact/signature compromise, unauthorized control action, teardown failure, audit integrity loss, widespread availability loss, and localized SLO degradation.
- [ ] **INV-71-C097-IMP-02** Map each severity to paging targets, acknowledgment/mitigation objectives, incident commander, security/legal/privacy notification paths, and vendor escalation.
- [ ] **INV-71-C097-IMP-03** Create containment playbooks for disable new sessions, revoke policy/artifact, quarantine node/site, cut egress, drain fleet, rotate credentials, and preserve forensic evidence.
- [ ] **INV-71-C097-IMP-04** Define recovery and re-entry criteria; do not return quarantined nodes/artifacts without requalification and trust re-establishment.
- [ ] **INV-71-C097-IMP-05** Run tabletop and live game-day exercises and track gaps to closure.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C097-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C097-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C097-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C097-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C097-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C097-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C097-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C097-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C097-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C097-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C097-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C097-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C097-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C098 — Perform recurring access, policy, dependency, configuration, and architecture reviews.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No recurring access/policy/dependency/configuration/architecture review process.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C098-IMP-01** Schedule recurring reviews for privileged access, service identities, break-glass use, authorization roles, egress policies, artifact allowlists, dependencies/SBOM vulnerabilities, configuration drift, and architecture changes.
- [ ] **INV-71-C098-IMP-02** Define review cadence by risk and require named reviewers independent of the change author for security-sensitive areas.
- [ ] **INV-71-C098-IMP-03** Automate drift reports comparing effective nodes/sites against approved configuration/artifact manifests.
- [ ] **INV-71-C098-IMP-04** Record findings, owners, due dates, exceptions, and evidence of remediation; escalate overdue critical findings.
- [ ] **INV-71-C098-IMP-05** Use review output to update threat model, ADRs, compatibility matrix, and deprecation/patch plans.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C098-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C098-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C098-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C098-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C098-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C098-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C098-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C098-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C098-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C098-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C098-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C098-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C098-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C099 — Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No exception/waiver/technical-debt/deprecation register with owners and expiry dates.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C099-IMP-01** Create a structured register for security exceptions, operational waivers, performance waivers, unsupported combinations, known technical debt, and deprecated behavior.
- [ ] **INV-71-C099-IMP-02** Require owner, rationale, affected scope, compensating controls, risk assessment, approval identity, creation date, expiry date, and removal plan.
- [ ] **INV-71-C099-IMP-03** Disallow permanent/ownerless waivers for security-critical invariants; expired waivers must fail release/deployment gates until renewed or removed.
- [ ] **INV-71-C099-IMP-04** Link waivers to requirements, code/config, incidents, tests, and release evidence so hidden debt cannot bypass certification.
- [ ] **INV-71-C099-IMP-05** Review the register on every release and at a fixed governance cadence.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C099-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C099-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C099-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C099-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C099-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C099-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C099-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C099-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C099-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C099-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C099-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C099-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C099-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

### INV-71-C100 — Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

**Audit status:** `MISSING`  
**Existing evidence:** None  
**Observed gap:** No formal production exit gate aggregating architecture through ownership readiness evidence.  
**Suggested evidence locations:** `runbooks/`, `governance/`, `release/`, `evidence/operations/`

#### Targeted engineering checklist

- [ ] **INV-71-C100-IMP-01** Create a formal production exit-gate manifest covering architecture/ownership, normative requirements, interfaces, implementation/configuration, security, resilience, performance, observability, testing, rollout/rollback, operations, and governance.
- [ ] **INV-71-C100-IMP-02** Require every control to be EVIDENCED with immutable proof or carry an explicitly approved, unexpired exception permitted by policy; do not treat PARTIAL as production-complete.
- [ ] **INV-71-C100-IMP-03** Require independent approvals from service owner, security, SRE/operations, and release authority for the exact release/artifact digests being promoted.
- [ ] **INV-71-C100-IMP-04** Make the gate verifier machine-executable and fail closed on missing evidence, signature/provenance mismatch, unsupported dependency combination, benchmark regression, or unresolved critical vulnerability.
- [ ] **INV-71-C100-IMP-05** Archive the signed gate result, evidence digest tree, release manifest, approvals, and rollback target so production status is reproducible later.

#### Specification, integration, and control-plane completeness

- [ ] **INV-71-C100-DES-01** Assign accountable owner, review cadence, approval authority, escalation route, and evidence-retention requirement.
- [ ] **INV-71-C100-DES-02** Make the procedure executable and auditable with explicit prerequisites, commands/actions, expected outputs, stop conditions, and rollback/containment steps.
- [ ] **INV-71-C100-DES-03** Exercise the procedure through drills/game days rather than accepting documentation-only completion.
- [ ] **INV-71-C100-DES-04** Integrate completion/expiry status into release/deployment gates so stale operational evidence cannot silently pass.

#### Verification and evidence

- [ ] **INV-71-C100-VER-01** Add positive, negative, and boundary test cases; include malformed/untrusted inputs and unauthorized callers where applicable.
- [ ] **INV-71-C100-VER-02** Add fault/timeout/restart coverage for any external dependency or multi-step operation touched by this control.
- [ ] **INV-71-C100-VER-03** Capture machine-readable test evidence with source revision, release version, host/environment fingerprint, effective configuration digest, artifact digests, and timestamps.
- [ ] **INV-71-C100-VER-04** Require zero unexplained critical/high-severity findings in the control's scope before marking it evidenced; track any accepted residual risk through the formal waiver register.
- [ ] **INV-71-C100-VER-05** Update `AUDIT_AFTER.json`/successor evidence only from verifiable artifacts; do not mark the control EVIDENCED from prose intent alone.

#### Exit criteria

- [ ] **INV-71-C100-GATE-01** Completion gate: implementation exists in the production path, is enabled by default for the supported profile(s), and has reproducible verification evidence.
- [ ] **INV-71-C100-GATE-02** All required artifacts/tests are linked from the requirements traceability matrix using immutable release identifiers/digests.
- [ ] **INV-71-C100-GATE-03** Operational owner and escalation path have reviewed the implementation and the relevant runbook has been exercised if the control affects production operations.
- [ ] **INV-71-C100-GATE-04** The production gate rejects a build/deployment when this control's required evidence is absent, stale, revoked, incompatible, or failing.

## Cross-cutting repository/package gaps

### INV71-X001 — External `pk_core` conformance dependency is absent

**Status:** `MISSING`  
**Gap:** The three legacy integration/conformance tests cannot execute unless the surrounding project provides a compatible `pk_core` package.

#### Implementation checklist

- [ ] **INV71-X001-IMP-01** Declare the exact supported `pk_core` package/source repository, semantic version range, API contract version, and cryptographic source/artifact digest.
- [ ] **INV71-X001-IMP-02** Choose and document dependency mode: vendored immutable package, workspace dependency, signed internal registry artifact, or explicitly optional integration; do not rely on ambient PYTHONPATH discovery in production certification.
- [ ] **INV71-X001-IMP-03** Add a lock/manifest entry and deterministic resolver that verifies package integrity before running conformance.
- [ ] **INV71-X001-IMP-04** Define behavior when `pk_core` is absent or incompatible: standalone reference tests may run, but production conformance status must be NOT_RUN/FAILED rather than silently skipped as passing.
- [ ] **INV71-X001-IMP-05** Add CI jobs that execute the `pk_core` list/run/gate/verify path against all supported versions and validate evidence schema compatibility.
- [ ] **INV71-X001-IMP-06** Capture `pk_core` version/digest in release evidence and traceability records.
- [ ] **INV71-X001-IMP-07** Add negative tests for corrupt evidence, incompatible versions, unavailable core, partial gate output, and signature/digest mismatch.
- [ ] **INV71-X001-IMP-08** Document ownership and escalation for `pk_core` interface changes and deprecation.

#### Verification / closure

- [ ] **INV71-X001-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X001-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X001-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X001-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X001-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

### INV71-X002 — Historical `MASTER.md` source artifact is unavailable

**Status:** `MISSING`  
**Gap:** The prior README referenced a master-prompt corpus that was not present in the uploaded source, so historical intent cannot be fully reconstructed from the package.

#### Implementation checklist

- [ ] **INV71-X002-IMP-01** Locate the authoritative historical `MASTER.md` or formally declare it unavailable after repository/source-of-truth review.
- [ ] **INV71-X002-IMP-02** If recovered, verify provenance, author/time/revision, and digest before reintroducing it; never fabricate a replacement and label it historical.
- [ ] **INV71-X002-IMP-03** Diff recovered requirements against `CHECKLIST.json`, `contract.py`, ADR, threat model, and current audit to identify lost or changed requirements.
- [ ] **INV71-X002-IMP-04** Record superseded requirements and rationale so historical text cannot silently override the approved current contract.
- [ ] **INV71-X002-IMP-05** If unrecoverable, create a provenance note documenting the gap, search scope, decision authority, and the currently authoritative replacement artifacts.
- [ ] **INV71-X002-IMP-06** Add package inventory tests so documentation cannot claim a bundled file that is absent.
- [ ] **INV71-X002-IMP-07** Preserve provenance metadata and digest of any recovered source in release evidence.

#### Verification / closure

- [ ] **INV71-X002-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X002-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X002-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X002-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X002-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

### INV71-X003 — Production microVM implementation is absent

**Status:** `MISSING`  
**Gap:** No Firecracker launcher/jailer integration, kernel/rootfs set, snapshot builder, network namespace/firewall layer, device policy, cgroup controller, or teardown orchestrator exists in the repository.

#### Implementation checklist

- [ ] **INV71-X003-IMP-01** Implement a privileged-minimal node runtime that creates one Firecracker microVM per heavyweight session and exposes only the declared control-plane interface.
- [ ] **INV71-X003-IMP-02** Integrate jailer/chroot/UID-GID isolation, minimized Linux capabilities, seccomp, cgroup v2 limits, explicit KVM/TAP permissions, and no broad host filesystem mounts.
- [ ] **INV71-X003-IMP-03** Build signed immutable guest kernel/rootfs artifacts and a snapshot pipeline with digest-addressed metadata, CPU compatibility constraints, and reproducible provenance.
- [ ] **INV71-X003-IMP-04** Create per-session writable block overlays/tmpfs and prove no writable layer is reused across sessions.
- [ ] **INV71-X003-IMP-05** Create per-session network namespace/TAP/veth plus host-side default-deny egress enforcement, destination binding, DNS policy, and connection accounting.
- [ ] **INV71-X003-IMP-06** Implement lifecycle reconciliation for Firecracker PID, API socket, cgroup, netns/TAP, overlay, mounts, vsock/console, and lease/ownership records.
- [ ] **INV71-X003-IMP-07** Implement teardown as a multi-phase destroy+verify operation; a session is not VERIFIED until all owned host resources are absent and durable evidence is emitted.
- [ ] **INV71-X003-IMP-08** Add node reboot/crash reconciliation that detects and safely destroys or quarantines orphaned resources.
- [ ] **INV71-X003-IMP-09** Run real-boundary security, fault, load, soak, and cross-session residue tests before production classification.

#### Verification / closure

- [ ] **INV71-X003-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X003-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X003-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X003-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X003-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

### INV71-X004 — Build/release provenance and CI metadata are absent

**Status:** `MISSING`  
**Gap:** There is no project-level build manifest, dependency lock, SBOM, CI workflow, artifact signing configuration, release provenance, or reproducible image build.

#### Implementation checklist

- [ ] **INV71-X004-IMP-01** Add a canonical project/build manifest and lock all language/system dependencies used to build the node agent, helpers, images, and tooling.
- [ ] **INV71-X004-IMP-02** Create hermetic/reproducible build steps for binaries, guest kernel/rootfs, policy bundle, and snapshots where reproducibility is technically feasible.
- [ ] **INV71-X004-IMP-03** Generate SBOMs and vulnerability scan reports for every release artifact.
- [ ] **INV71-X004-IMP-04** Sign release manifests and artifacts with managed keys and publish provenance containing source commit, builder identity, recipe, dependency digests, and timestamps.
- [ ] **INV71-X004-IMP-05** Create CI stages for lint/static analysis, unit, contract, integration, security, fuzz, fault, performance, packaging, signature verification, and production gate evidence.
- [ ] **INV71-X004-IMP-06** Protect release branches/tags, require reviewed changes, and separate build authority from production promotion authority.
- [ ] **INV71-X004-IMP-07** Store immutable release evidence and verify it again at deploy time rather than trusting CI status alone.
- [ ] **INV71-X004-IMP-08** Test rebuild/reproduce and artifact-tamper scenarios regularly.

#### Verification / closure

- [ ] **INV71-X004-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X004-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X004-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X004-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X004-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

### INV71-X005 — Repository license is unspecified

**Status:** `MISSING`  
**Gap:** The package contains no LICENSE file, so redistribution/use terms are not defined by the artifact itself.

#### Implementation checklist

- [ ] **INV71-X005-IMP-01** Have the repository owner/legal authority select the intended license and confirm rights for all bundled or vendored code/artifacts.
- [ ] **INV71-X005-IMP-02** Add the complete license text at repository root and, where appropriate, SPDX identifiers in source/package metadata.
- [ ] **INV71-X005-IMP-03** Add third-party notices/attribution for Firecracker, kernel/rootfs packages, libraries, test corpora, and copied specifications as required by their licenses.
- [ ] **INV71-X005-IMP-04** Generate a dependency license inventory during build and fail release on prohibited/unknown licenses according to organizational policy.
- [ ] **INV71-X005-IMP-05** Document licensing of generated images/snapshots and any redistributable guest packages separately from the Python reference model.
- [ ] **INV71-X005-IMP-06** Add CI validation that `LICENSE`/NOTICE files and SPDX metadata are present and consistent.
- [ ] **INV71-X005-IMP-07** Include license inventory in release evidence.

#### Verification / closure

- [ ] **INV71-X005-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X005-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X005-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X005-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X005-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

### INV71-X006 — Secure memory/state erasure guarantee is absent

**Status:** `MISSING`  
**Gap:** Clearing Python containers cannot prove host allocator pages, guest RAM, swap, caches, or backing blocks are zeroized before reuse.

#### Implementation checklist

- [ ] **INV71-X006-IMP-01** Define the residual-data threat model across guest RAM, host process memory, swap, page cache, KSM/dedup, huge pages, writable block overlays, discard/TRIM, image caches, crash dumps, and hibernation.
- [ ] **INV71-X006-IMP-02** Avoid host swap for sensitive VMM/guest memory where required or encrypt it with managed keys; define core-dump policy and disable/secure dumps for privileged runtime processes.
- [ ] **INV71-X006-IMP-03** Ensure microVM memory is never reused by another tenant without kernel/hypervisor allocation semantics that provide zeroed pages; validate the exact host-kernel behavior for supported versions.
- [ ] **INV71-X006-IMP-04** Use per-session encrypted ephemeral block state where feasible so key destruction provides cryptographic erasure in addition to file deletion/discard.
- [ ] **INV71-X006-IMP-05** Destroy writable overlays and verify backing-file/block mapping is not reused as trusted clean state; sanitize snapshot/build pipelines against accidental secret capture.
- [ ] **INV71-X006-IMP-06** Define page-cache/KSM/shared-memory policy and prohibit cross-tenant memory deduplication if it undermines the isolation model.
- [ ] **INV71-X006-IMP-07** Create residue tests that write identifiable patterns/secrets, teardown, churn allocator/storage, and attempt recovery from a later session and host forensic interfaces.
- [ ] **INV71-X006-IMP-08** Document what cannot be absolutely proven and require an explicit residual-risk acceptance for the chosen hardware/kernel/storage model.

#### Verification / closure

- [ ] **INV71-X006-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X006-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X006-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X006-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X006-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

### INV71-X007 — DNS-to-destination enforcement is absent

**Status:** `MISSING`  
**Gap:** Hostname canonicalization alone does not prevent DNS rebinding or bind policy to the actual IP destination reached on the network.

#### Implementation checklist

- [ ] **INV71-X007-IMP-01** Define whether policy is host-based, IP/CIDR-based, service-identity-based, proxy-based, or a combination; make the enforcement point external to the guest.
- [ ] **INV71-X007-IMP-02** Resolve allowed hostnames through a controlled resolver and bind each connection to the resolved approved address set; enforce destination IP+port/protocol at firewall/proxy time.
- [ ] **INV71-X007-IMP-03** Handle DNS rebinding by revalidating resolution according to bounded TTL/freshness rules and never trusting guest-supplied DNS answers for policy.
- [ ] **INV71-X007-IMP-04** Define CNAME chains, IPv4/IPv6, private/link-local/loopback/metadata ranges, IDNA/punycode, trailing dots, zone IDs, literal IPs, redirects, proxy CONNECT, and SNI/Host mismatch behavior.
- [ ] **INV71-X007-IMP-05** Prevent time-of-check/time-of-use races by performing resolution and connect through the same trusted enforcement component or by passing an authenticated resolved-destination capability.
- [ ] **INV71-X007-IMP-06** Log requested host, canonical host, resolved addresses, selected destination, policy version, allow/deny reason, and connection identity without leaking unrelated tenant data.
- [ ] **INV71-X007-IMP-07** Test malicious DNS server, rapid TTL changes, rebinding from public to private/metadata IP, split-horizon DNS, dual-stack preference, redirect chains, and stale-cache behavior.
- [ ] **INV71-X007-IMP-08** Fail closed when destination identity cannot be verified according to policy.

#### Verification / closure

- [ ] **INV71-X007-VER-01** Add automated verification that fails if the gap regresses or the required artifact/capability disappears.
- [ ] **INV71-X007-VER-02** Record accountable owner, dependencies, rollout/rollback or recovery path, and residual risks.
- [ ] **INV71-X007-VER-03** Emit machine-readable evidence with source/release/artifact/configuration digests.
- [ ] **INV71-X007-VER-04** Link the evidence to the applicable INV-71 controls in the traceability matrix and production gate.
- [ ] **INV71-X007-VER-05** Close only after production-equivalent verification succeeds and the second audit finds no remaining untracked gap in this scope.

## Final production-certification checklist

- [ ] **FINAL-01** All 100 INV-71 controls are EVIDENCED, or any allowed exception is documented in the signed waiver register with owner, compensating controls, and unexpired approval.
- [ ] **FINAL-02** The real microVM boundary—not the Python reference model—passes isolation, egress, resource, teardown, adversarial, fault, compatibility, load, and soak tests.
- [ ] **FINAL-03** All release/runtime artifacts are pinned, SBOM-described, provenance-recorded, signed, verified, and within vulnerability/EOL policy.
- [ ] **FINAL-04** Node/control-plane identities, authorization, secret handling, encryption, network destination enforcement, and audit durability are enabled and tested fail closed.
- [ ] **FINAL-05** Rollback, emergency disable, quarantine, incident response, backup/reconstruction, certificate/key rotation, and node requalification have been exercised in production-equivalent game days.
- [ ] **FINAL-06** Performance/capacity thresholds and telemetry are measured on supported deployment profiles and enforced by automated gates/admission controls.
- [ ] **FINAL-07** Mixed-version and rolling-upgrade tests prove supported skew; unsupported combinations are rejected automatically.
- [ ] **FINAL-08** No leaked Firecracker process, cgroup, netns/TAP, mount, overlay, socket, descriptor, secret, memory/state residue, or stale ownership record remains after teardown/recovery tests.
- [ ] **FINAL-09** The signed release evidence bundle and gate result can be independently reverified and reproduces the claimed production status.
- [ ] **FINAL-10** Named owners formally accept production responsibility for the exact release and its documented residual risks.

