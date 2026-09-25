# INV-70 Fast Agent Sandbox v4.2.0 — Missing Components Remediation Master Checklist

**Baseline:** INV-70 v4.2.0 hardened repository  
**Source of truth:** `AUDIT_MATRIX_4.2.0.json`  
**Scope:** Every requirement currently marked `MISSING` (50/50), converted into an engineering-ready remediation checklist.  
**Purpose:** Implementation planning, technical handoff, verification, and production-readiness evidence.

## Completion semantics

- `[ ]` means the work or evidence is not yet complete; `[x]` should be used only when objective evidence exists.
- **P0** = architecture/security/release-control blocker; **P1** = production-readiness blocker that normally follows core architecture; **P2** = optimization/governance maturity item that still remains required by the source checklist.
- A component is not complete merely because documentation exists. Where the requirement is behavioral, both implementation and automated verification are required.
- Required evidence should be content-addressed or tied to a release/source/configuration digest wherever practical.
- Any `WAIVED` status must use the formal exception register from INV-70-C099 and must not be substituted for a silent skip.
- Existing v4.2.0 files (`runtime.py`, `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, `CHECKLIST.json`, tests, and audit artifacts) should be updated rather than contradicted by parallel documentation.

## Recommended dependency order

1. **Governance/architecture foundation:** C009, C010, C012, C015, C019, C020.
2. **Production execution and interface controls:** C023, C025, C027, C031, C035, C036, C037.
3. **Trust and security enforcement:** C044, C045, C048, C049.
4. **Resilience:** C053, C054, C055, C056, C058, C060.
5. **Observability and operator explainability:** C072–C080 missing items.
6. **Testing/certification:** C030, C083, C084, C085, C088, C089, C090.
7. **Performance engineering/gates:** C061, C063–C068 missing items, C070.
8. **Release/operations governance:** C093, C094, C097, C098, C099.

## Master index

| ID | Priority | Dimension | Work package |
|---|---|---|---|
| INV-70-C009 | P0 | Architecture & Scope | Accountable ownership and escalation |
| INV-70-C010 | P0 | Architecture & Scope | Approved architecture decision record for execution technology |
| INV-70-C012 | P1 | Requirements & Semantics | Deployment-context applicability and requirements matrix |
| INV-70-C015 | P1 | Requirements & Semantics | Execution lifecycle state model |
| INV-70-C019 | P0 | Requirements & Semantics | Constraint-conflict precedence policy |
| INV-70-C020 | P0 | Requirements & Semantics | Requirements traceability matrix (RTM) |
| INV-70-C023 | P0 | Interfaces & Integration | Boundary authentication model |
| INV-70-C025 | P0 | Interfaces & Integration | Timeout, cancellation, retry, idempotency, and backpressure contract |
| INV-70-C027 | P1 | Interfaces & Integration | Mixed-version compatibility and negotiation |
| INV-70-C030 | P0 | Interfaces & Integration | Adjacent-layer integration test suite |
| INV-70-C031 | P0 | Implementation & Configuration | Pinned per-operation Wasm sandbox implementation |
| INV-70-C035 | P1 | Implementation & Configuration | Site/environment configuration overlays |
| INV-70-C036 | P1 | Implementation & Configuration | Configuration provenance and activation record |
| INV-70-C037 | P0 | Implementation & Configuration | Atomic/transactional configuration activation |
| INV-70-C044 | P0 | Security, Trust & Isolation | Node, peer, artifact, provider, and control-plane authentication/attestation |
| INV-70-C045 | P0 | Security, Trust & Isolation | Executable/policy artifact integrity, provenance, SBOM, and version verification |
| INV-70-C048 | P0 | Security, Trust & Isolation | Safe behavior when critical trust/time services are unavailable |
| INV-70-C049 | P0 | Security, Trust & Isolation | Tamper-evident security audit event pipeline |
| INV-70-C053 | P1 | Resilience & Failure Handling | Bounded safe-retry policy with backoff and jitter |
| INV-70-C054 | P0 | Resilience & Failure Handling | Admission control, load shedding, and circuit breaking |
| INV-70-C055 | P1 | Resilience & Failure Handling | Failover policy preserving isolation, residency, and consistency |
| INV-70-C056 | P1 | Resilience & Failure Handling | Defined degraded-operation modes |
| INV-70-C058 | P0 | Resilience & Failure Handling | Duplicate execution and stale-controller protection |
| INV-70-C060 | P1 | Resilience & Failure Handling | Fault-injection and recovery certification |
| INV-70-C061 | P1 | Performance & Resource Efficiency | Reproducible performance and resource baseline |
| INV-70-C063 | P1 | Performance & Resource Efficiency | Steady, burst, overload, scale, and recovery performance suite |
| INV-70-C064 | P2 | Performance & Resource Efficiency | Per-workload and per-tenant overhead measurement |
| INV-70-C065 | P2 | Performance & Resource Efficiency | Serialization/copy/context-switch/network-hop/state duplication analysis |
| INV-70-C066 | P2 | Performance & Resource Efficiency | Measured locality/caching/batching/zero-copy optimizations |
| INV-70-C068 | P2 | Performance & Resource Efficiency | Edge-node power and thermal characterization |
| INV-70-C070 | P1 | Performance & Resource Efficiency | Blocking performance-regression release gate |
| INV-70-C072 | P0 | Observability & Explainability | Runtime structured metrics implementation |
| INV-70-C073 | P0 | Observability & Explainability | Structured logging with stable correlation identifiers |
| INV-70-C074 | P1 | Observability & Explainability | Distributed trace-context propagation |
| INV-70-C075 | P1 | Observability & Explainability | Safe high-cardinality diagnostic channel |
| INV-70-C077 | P1 | Observability & Explainability | Operator-readable explain view |
| INV-70-C078 | P1 | Observability & Explainability | Correlation to release lineage and live infrastructure graph |
| INV-70-C079 | P1 | Observability & Explainability | Telemetry retention, sampling, privacy, and export policy |
| INV-70-C080 | P1 | Observability & Explainability | Operational dashboards, alerts, and diagnostic classification |
| INV-70-C083 | P0 | Testing & Certification | Integration certification across all supported layers and tiers |
| INV-70-C084 | P1 | Testing & Certification | Cross-platform/runtime/provider/protocol compatibility matrix |
| INV-70-C085 | P0 | Testing & Certification | Fuzzing and property-based testing of untrusted inputs/boundaries |
| INV-70-C088 | P1 | Testing & Certification | Benchmark, soak, burst, and fleet-scale certification |
| INV-70-C089 | P1 | Testing & Certification | Disaster, partition, reconnect, and degraded-control-plane tests |
| INV-70-C090 | P0 | Testing & Certification | Machine-readable production release acceptance evidence |
| INV-70-C093 | P1 | Operations, Release & Governance | Supported-version compatibility matrix and enforcement |
| INV-70-C094 | P0 | Operations, Release & Governance | Patching, vulnerability response, and end-of-life policy |
| INV-70-C097 | P0 | Operations, Release & Governance | Incident severity, paging, containment, and recovery procedures |
| INV-70-C098 | P2 | Operations, Release & Governance | Recurring access, policy, dependency, configuration, and architecture reviews |
| INV-70-C099 | P1 | Operations, Release & Governance | Exception, waiver, technical-debt, and deprecation register |

# Architecture & Scope

## INV-70-C009 — Accountable ownership and escalation

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `OWNERS.md`  
> Tests/evidence: `tests/test_governance.py::Docs`  
> Remaining: Accountable owner named. On-call alias, security reviewer and reliability reviewer are UNASSIGNED placeholders - the owner must name them.

**Priority:** P0  
**Canonical requirement:** Assign an accountable owner and escalation path for Fast agent sandbox.  
**Current v4.2.0 gap:** No accountable human/team owner, on-call alias, or escalation path is shipped.

**Target artifacts**
- [ ] `OWNERS.yaml`
- [ ] `OPERATIONS.md`
- [ ] `CODEOWNERS (or equivalent repository ownership rule)`

### Engineering implementation checklist

- [ ] Define a stable service/team owner identifier for INV-70; do not use an individual-only ownership model.
- [ ] Define named roles for engineering owner, security owner, runtime/platform owner, operations/SRE owner, and release approver.
- [ ] Define primary and secondary on-call aliases or escalation targets for production-impacting failures.
- [ ] Define an escalation ladder with acknowledgement targets, hand-off rules, and the authority to disable the sandbox or individual capabilities.
- [ ] Map each operational responsibility to a RACI-style role: runtime defects, capability incidents, dependency failures, vulnerability response, release approval, rollback, and evidence retention.
- [ ] Define ownership boundaries with INV-69, INV-09, INV-71, and GAP-09 so incidents are not bounced between teams.
- [ ] Define coverage for weekends/holidays and what happens when the primary owner is unreachable.
- [ ] Add a machine-readable ownership record with fields such as element_id, team, role, contact_alias, escalation_level, effective_from, and review_due.
- [ ] Add repository ownership protection so changes to runtime.py, SECURITY.md, compatibility data, and release evidence require review by the appropriate owner class.
- [ ] Document the emergency authority path for revoking a capability, rolling back a runtime release, or forcing fail-closed admission.

### Verification and adversarial test checklist

- [ ] Validate OWNERS.yaml against a schema in CI and reject missing/placeholder owners.
- [ ] Exercise a tabletop escalation from a trapped workload through security escalation and release rollback.
- [ ] Check every linked dependency has an explicit responsibility transfer point and escalation target.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] No production-critical responsibility is ownerless.
- [ ] At least two escalation paths exist for every P0/P1 class incident.
- [ ] Ownership metadata is referenced by the release and incident runbooks.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C010 — Approved architecture decision record for execution technology

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `docs/adr/ADR-0001-execution-technology.md`  
> Tests/evidence: `tests/test_governance.py::Docs`  
> Remaining: ADR drafted with options, decision and consequences; status PROPOSED until the owner and security reviewer sign the approval block.

**Priority:** P0  
**Canonical requirement:** Approve an architecture decision record for Fast agent sandbox, its technologies (Per-operation Wasm sandbox), and its function (Stateless calculations, transforms, and tools).  
**Current v4.2.0 gap:** No approved ADR exists; additionally, the required per-operation Wasm technology is not implemented.

**Target artifacts**
- [ ] `docs/adr/ADR-0001-fast-agent-sandbox.md`
- [ ] `docs/architecture/fast-agent-sandbox-context.md`

### Engineering implementation checklist

- [ ] Write an ADR that explicitly records the current v4.2.0 custom Python stack VM and the checklist-required target of a per-operation Wasm sandbox.
- [ ] State the production function: bounded stateless calculations, transforms, and capability-mediated tools; identify non-goals such as arbitrary native code and persistent state.
- [ ] Document the isolation boundary and state that Python host callbacks remain trusted ambient-authority code unless moved behind a stronger process/runtime boundary.
- [ ] Decide whether the Python VM is retained only as a reference/intermediate implementation, removed, or supported as a non-production profile; record the migration rule.
- [ ] Define the target Wasm execution model: fresh instance per operation, module validation before instantiation, no ambient filesystem/network/device access, and explicit imported capabilities only.
- [ ] Define the Wasm ABI/WIT strategy for run input, result output, host calls, cancellation/deadlines, and structured traps.
- [ ] Define resource controls: fuel/instruction budget, linear-memory maximum, table/global limits, stack/call-depth policy, module size, output size, and wall-clock deadline.
- [ ] Document determinism expectations and sources of nondeterminism such as time, randomness, host I/O, scheduling, and floating-point behavior.
- [ ] Document artifact trust requirements: digest pinning, signature/provenance verification, approved module/runtime versions, and SBOM linkage.
- [ ] Document operational assumptions for process isolation, sandbox escape response, runtime CVEs, module caching, and runtime upgrades.
- [ ] List considered alternatives and tradeoffs, including retaining the Python VM, using a separate worker process, and using a pinned Wasm runtime.
- [ ] Include rollback/migration criteria and explicit approval/sign-off fields for architecture, security, and operations.

### Verification and adversarial test checklist

- [ ] Review the ADR against contract.py, RUNTIME_SPEC.md, SECURITY.md, and CHECKLIST.json for contradictory claims.
- [ ] Run an architecture review proving every trust boundary and privileged component has an owner and control.
- [ ] Fail release certification if the ADR is unapproved, superseded without replacement, or inconsistent with the selected runtime.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] The production execution technology and isolation boundary are unambiguous.
- [ ] The ADR explicitly resolves the Python-VM-versus-Wasm mismatch rather than masking it.
- [ ] All runtime, security, and integration work packages cite the ADR decision.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Requirements & Semantics

## INV-70-C012 — Deployment-context applicability and requirements matrix

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `docs/DEPLOYMENT_MATRIX.md`, `config.py::ENVIRONMENTS`  
> Tests/evidence: `tests/test_config.py::Overlays.test_every_environment_resolves`, `tests/test_integration.py::DevAndEdgeTiers`  

**Priority:** P1  
**Canonical requirement:** Define functional requirements for Fast agent sandbox across cloud, datacenter, near-edge, and far-edge contexts where applicable.  
**Current v4.2.0 gap:** No cloud/datacenter/near-edge/far-edge applicability and behavior matrix.

**Target artifacts**
- [ ] `docs/DEPLOYMENT_PROFILES.md`
- [ ] `config/deployment-profiles.schema.json`
- [ ] `config/deployment-profiles.yaml`

### Engineering implementation checklist

- [ ] Define supported deployment contexts: cloud, datacenter, near-edge, and far-edge; mark each as supported, conditional, experimental, or unsupported.
- [ ] For each context, record CPU architecture, OS/runtime assumptions, minimum memory, storage constraints, expected network quality, clock availability, trust/attestation services, and power constraints.
- [ ] Define per-context sandbox defaults for fuel, max stack, logical memory, Wasm linear memory, module size, host-call concurrency, wall-clock deadline, and telemetry sampling.
- [ ] Define which capabilities are permitted or prohibited by context, especially network, local device, secret, and filesystem-like capabilities.
- [ ] Define residency/locality rules describing whether execution and host calls may fail over to another site or region.
- [ ] Define behavior for intermittent or offline edge operation, including which configuration/policy data may be cached and its maximum validity window.
- [ ] Define observability behavior when export is unavailable, including bounded local buffering and data-loss semantics.
- [ ] Define security prerequisites for each profile, including workload identity, node identity/attestation, trusted time, and signature-verification roots.
- [ ] Create a machine-readable profile schema with explicit defaults and no silent fallback from an unsupported context.
- [ ] Bind runtime configuration selection to a validated deployment_profile identifier rather than ad-hoc environment branching.
- [ ] Document unsupported combinations and the exact admission rejection reason for each.

### Verification and adversarial test checklist

- [ ] Run profile-validation tests for every supported/unsupported context and boundary value.
- [ ] Execute at least one conformance run per supported context class or an approved representative hardware profile.
- [ ] Verify a workload cannot request a less restrictive deployment profile than the node/site policy permits.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every advertised deployment context has testable requirements and defaults.
- [ ] Unsupported contexts fail deterministically before guest execution.
- [ ] Profile selection is included in run evidence and telemetry.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C015 — Execution lifecycle state model

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `semantics.py::Lifecycle`, `RUNTIME_SPEC.md#lifecycle`  
> Tests/evidence: `tests/test_semantics.py::LifecycleTests`  

**Priority:** P1  
**Canonical requirement:** Define lifecycle states and legal state transitions managed or exposed by Fast agent sandbox.  
**Current v4.2.0 gap:** No lifecycle state model or legal transition table.

**Target artifacts**
- [ ] `docs/EXECUTION_LIFECYCLE.md`
- [ ] `schemas/run-state.schema.json`

### Engineering implementation checklist

- [ ] Define a finite state machine for a sandbox operation, including at minimum RECEIVED, VALIDATING, REJECTED, ADMITTED, INSTANTIATING, RUNNING, HOSTCALL_WAIT, SUCCEEDED, TRAPPED, CANCELLED, DEADLINE_EXCEEDED, and CLEANED_UP as applicable.
- [ ] Define legal transitions, terminal states, and forbidden transitions; make terminal result publication monotonic.
- [ ] Define when a run_id/operation_id is allocated and how it remains stable across retries, tracing, logs, and evidence.
- [ ] Define admission failure versus runtime trap semantics so policy/auth/resource rejection is not misreported as guest failure.
- [ ] Define cancellation semantics at each state, including pre-start cancellation and cancellation during a host call.
- [ ] Define deadline semantics and whether wall-clock timeout is enforced by the runtime, a worker process, or the embedding layer.
- [ ] Define cleanup guarantees for Wasm instances, host-call handles, temporary buffers, metrics/traces, and deduplication records.
- [ ] Define crash/restart behavior for an in-flight operation and whether it can be safely reissued.
- [ ] Define state exposure rules so operators can diagnose a run without exposing guest payloads or secrets.
- [ ] Add machine-readable termination reason codes separate from human-readable text.
- [ ] Update PK_FASTBOX_RUN/1 and PK_FASTBOX_RESULT/1 specifications to reference lifecycle semantics.

### Verification and adversarial test checklist

- [ ] Add state-transition unit/property tests covering every legal edge and representative illegal transitions.
- [ ] Inject cancellation/deadline at each nonterminal state and verify exactly one terminal result and cleanup path.
- [ ] Crash the embedding worker at selected states and validate retry/duplicate-execution behavior.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every run ends in exactly one terminal state with a stable reason code.
- [ ] No illegal transition can be produced by public interfaces.
- [ ] Lifecycle state and terminal reason are emitted consistently to logs, metrics, traces, and evidence.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C019 — Constraint-conflict precedence policy

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `semantics.py::resolve_conflict`, `docs/PRECEDENCE.md`, `service.py (capability intersection, fuel tightening)`  
> Tests/evidence: `tests/test_semantics.py::Precedence`, `tests/test_integration.py::ProdPath.test_capability_requires_token_grant`  

**Priority:** P0  
**Canonical requirement:** Define precedence rules when Fast agent sandbox requirements conflict with security, residency, SLO, or cost constraints.  
**Current v4.2.0 gap:** No precedence policy for conflicts among security, residency, SLO, and cost.

**Target artifacts**
- [ ] `docs/POLICY_PRECEDENCE.md`
- [ ] `schemas/constraint-decision.schema.json`

### Engineering implementation checklist

- [ ] Enumerate constraint classes that can conflict: security, isolation, tenant separation, residency, legal/compliance, correctness, availability/SLO, latency, cost, power/thermal, and operator override.
- [ ] Define which classes are non-overridable hard constraints and which may be optimized or degraded under an approved policy.
- [ ] Define deterministic precedence rules rather than relying on implementation order or whichever subsystem responds first.
- [ ] Define how multiple policies at tenant, environment, site, workload, and global levels compose and which scope has precedence.
- [ ] Define conflict-resolution output containing decision, winning constraint, rejected alternative, policy/config version, and stable reason code.
- [ ] Define behavior when the precedence policy itself is unavailable, invalid, expired, or ambiguous; default to a documented safe state.
- [ ] Define whether operator emergency overrides exist, who may invoke them, maximum duration, audit requirements, and constraints that can never be overridden.
- [ ] Define residency-versus-failover behavior explicitly so availability does not silently move execution across a forbidden boundary.
- [ ] Define cost/latency optimization only after mandatory security and residency predicates pass.
- [ ] Add examples covering overload, dependency outage, edge disconnection, failover, expired attestation, and telemetry failure.

### Verification and adversarial test checklist

- [ ] Create table-driven tests for every pairwise and high-risk multi-constraint conflict.
- [ ] Property-test that hard security/residency constraints never lose to cost or SLO preferences.
- [ ] Verify every conflict produces a deterministic reason code and explain record.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] No security-critical decision depends on undocumented ordering.
- [ ] Precedence decisions are reproducible from recorded policy/config inputs.
- [ ] Overrides are time-bounded, authenticated, and tamper-evidently audited.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C020 — Requirements traceability matrix (RTM)

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `requirements/RTM.yaml`, `tools/remediation_status.py`  
> Tests/evidence: `tests/test_governance.py::RTM`  

**Priority:** P0  
**Canonical requirement:** Maintain a requirements traceability matrix from each Fast agent sandbox requirement to implementation and verification evidence.  
**Current v4.2.0 gap:** No requirements traceability matrix mapping all 100 requirements to implementation and evidence.

**Target artifacts**
- [ ] `requirements/RTM.yaml`
- [ ] `tools/validate_rtm.py`
- [ ] `evidence/requirements/`

### Engineering implementation checklist

- [ ] Create one RTM row for every requirement in CHECKLIST.json, preserving the canonical check_id and requirement text.
- [ ] For each row, link design artifact(s), implementation file/symbol(s), test case(s), operational control(s), evidence file(s), and current certification status.
- [ ] Distinguish IMPLEMENTED, PARTIAL, MISSING, NOT_APPLICABLE, WAIVED, and VERIFIED states; require rationale for N/A and waiver states.
- [ ] Attach immutable identifiers where possible: git path plus symbol, test node ID, evidence digest, ADR ID, schema ID, and release version.
- [ ] Add fields for owner, last_verified_at, verification_method, evidence_digest, and expiration/review date when evidence can become stale.
- [ ] Generate human-readable Markdown from the machine-readable RTM so the two cannot drift.
- [ ] Link the existing AUDIT_MATRIX_4.2.0.json as historical audit input, not as production acceptance evidence.
- [ ] Add CI validation that all 100 checklist IDs are represented exactly once and no orphan/duplicate IDs exist.
- [ ] Add CI validation that referenced local files/tests exist and that VERIFIED items have at least one verification evidence reference.
- [ ] Prevent a requirement from being marked VERIFIED solely because documentation exists when executable verification is required.
- [ ] Carry RTM version and digest into release acceptance evidence.

### Verification and adversarial test checklist

- [ ] Delete or rename a referenced test in a negative CI fixture and verify the RTM validator fails.
- [ ] Inject duplicate/missing checklist IDs and verify schema/integrity checks fail.
- [ ] Compare generated RTM counts with CHECKLIST.json and release evidence on every build.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] All 100 canonical requirements are traceable end-to-end.
- [ ] Every VERIFIED claim resolves to concrete, reviewable evidence.
- [ ] RTM validation is a blocking release gate.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Interfaces & Integration

## INV-70-C023 — Boundary authentication model

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `security.py::Authenticator`, `docs/INTERFACES.md#authentication`  
> Tests/evidence: `tests/test_security.py::AuthTests`, `tests/test_integration.py::ProdPath.test_unauthenticated_rejected_before_execution`  
> Remaining: Residual: HMAC key-id verifier; ADR-0001 records the move to asymmetric keys via the Verifier seam.

**Priority:** P0  
**Canonical requirement:** Define authentication requirements at each Fast agent sandbox boundary.  
**Current v4.2.0 gap:** No authentication model for caller, workload, node, peer, artifact, or control plane.

**Target artifacts**
- [ ] `docs/AUTHENTICATION.md`
- [ ] `schemas/principal.schema.json`
- [ ] `schemas/run-auth-context.schema.json`

### Engineering implementation checklist

- [ ] Enumerate every trust boundary: caller→INV-70, workload→runtime, node→control plane, peer layer→INV-70, artifact→runtime, provider→runtime, and operator/control-plane actor→configuration/release APIs.
- [ ] Define a canonical principal model containing subject, tenant, workload, trust domain, credential type, issuer, audience, authentication strength, and expiry.
- [ ] Define accepted credential mechanisms for each boundary (for example workload identity/mTLS tokens) without allowing unauthenticated fallback in production profiles.
- [ ] Separate authentication from capability authorization: a valid identity must not automatically receive a host capability.
- [ ] Bind tenant/workload identity to the run request and prevent the guest program from modifying that identity context.
- [ ] Authenticate node and peer identities before accepting control or routing instructions.
- [ ] Authenticate executable/policy artifacts by digest/signature/provenance rather than filename or mutable path.
- [ ] Define credential expiry, clock-skew bounds, replay protection, nonce/request binding where required, and key rotation/revocation behavior.
- [ ] Define trust-domain federation rules and explicitly reject unknown issuers/audiences.
- [ ] Ensure authentication failures produce stable non-sensitive reason codes and never reach guest execution.
- [ ] Add an authentication context to audit, trace, and explain outputs using privacy-safe identifiers.

### Verification and adversarial test checklist

- [ ] Test valid, expired, wrong-audience, wrong-tenant, revoked, replayed, and unknown-issuer credentials.
- [ ] Verify authenticated-but-unauthorized principals cannot invoke ungranted capabilities.
- [ ] Verify guest payloads cannot spoof node, tenant, workload, or operator identity fields.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every production boundary has a defined authentication mechanism and trust root.
- [ ] Authentication happens before authorization/admission and is fail-closed.
- [ ] Credential and identity events are observable without leaking secrets.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C025 — Timeout, cancellation, retry, idempotency, and backpressure contract

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `resilience.py::Deadline/CancelToken/IdempotencyCache`, `executor.py::ProcessExecutor`, `docs/INTERFACES.md#timeouts`  
> Tests/evidence: `tests/test_resilience.py`, `tests/test_integration.py::Faults.test_wall_clock_preemption`, `tests/test_integration.py::ProdPath.test_idempotency`  

**Priority:** P0  
**Canonical requirement:** Define timeout, cancellation, retry, idempotency, and backpressure semantics for Fast agent sandbox.  
**Current v4.2.0 gap:** No timeout/cancellation/retry/idempotency/backpressure contract for host calls or orchestration.

**Target artifacts**
- [ ] `docs/REQUEST_SEMANTICS.md`
- [ ] `schemas/run-control.schema.json`
- [ ] `schemas/hostcall-control.schema.json`

### Engineering implementation checklist

- [ ] Define separate budgets for queue/admission wait, sandbox startup, guest execution, individual host calls, and total end-to-end operation time.
- [ ] Add explicit deadline/cancellation fields to run and host-call contracts; use an absolute or monotonic-deadline representation that avoids repeated timeout inflation.
- [ ] Define who enforces each deadline and ensure a blocking Python host callback cannot defeat the end-to-end deadline; use a preemptible process/task boundary where necessary.
- [ ] Define cancellation propagation from caller to running guest and from guest/runtime to in-flight host calls.
- [ ] Define retry eligibility by operation class; never automatically retry side-effecting calls without an idempotency contract.
- [ ] Define idempotency_key/operation_id semantics and retention window for duplicate suppression at the appropriate boundary.
- [ ] Define backpressure signals, bounded queue lengths, concurrency ceilings, and overload rejection codes instead of unbounded buffering.
- [ ] Define Retry-After or equivalent hints only when a retry is safe and capacity recovery is plausible.
- [ ] Define partial-result semantics: a cancelled/timed-out execution must not publish a success value.
- [ ] Define how fuel exhaustion differs from wall-clock deadline, dependency timeout, and cancellation.
- [ ] Propagate control semantics to telemetry and evidence using stable reason codes.

### Verification and adversarial test checklist

- [ ] Race cancellation against completion and verify at-most-one terminal result.
- [ ] Simulate hung/slow host callbacks and prove total deadline enforcement outside the trusted callback.
- [ ] Flood the admission path past configured concurrency/queue limits and verify bounded memory plus deterministic overload rejection.
- [ ] Replay the same idempotency key across safe and side-effecting host calls and verify the documented behavior.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] No request can wait or execute indefinitely under production embedding.
- [ ] Retries cannot create duplicate side effects under the documented contract.
- [ ] Backpressure is explicit, bounded, measurable, and test-covered.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C027 — Mixed-version compatibility and negotiation

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `semantics.py::negotiate/downgrade_result`  
> Tests/evidence: `tests/test_semantics.py::Versions`, `tests/test_integration.py::ProdPath.test_ok_v2_and_v1`  

**Priority:** P1  
**Canonical requirement:** Define compatibility behavior when peers use different supported versions.  
**Current v4.2.0 gap:** No peer-version negotiation or mixed-version compatibility rules.

**Target artifacts**
- [ ] `COMPATIBILITY.yaml`
- [ ] `docs/VERSIONING.md`
- [ ] `tests/compatibility/`

### Engineering implementation checklist

- [ ] Define independent versions for package release, run/result protocol, host-call protocol, WIT/ABI surface, configuration schema, and evidence schema.
- [ ] Define compatibility policy for major/minor/patch changes and which changes require a new protocol/ABI version.
- [ ] Add a peer capability/version handshake before using optional features or new fields.
- [ ] Define lowest-common-denominator negotiation and explicitly forbid silent semantic downgrade for security controls.
- [ ] Define unknown-field, unknown-opcode, unknown-capability, and unknown-termination-code behavior.
- [ ] Define rolling upgrade rules for N/N-1 or another approved window without assuming all peers upgrade simultaneously.
- [ ] Define downgrade behavior and conditions under which an older peer must be rejected rather than supported.
- [ ] Define compatibility for cached modules/artifacts/configuration created by another supported version.
- [ ] Record negotiated versions in trace/explain/evidence output.
- [ ] Publish end-of-support metadata for protocol/ABI versions in the compatibility matrix.

### Verification and adversarial test checklist

- [ ] Build pairwise mixed-version tests across every supported adjacent version combination.
- [ ] Test security-sensitive feature mismatch and prove negotiation fails closed rather than disabling the feature.
- [ ] Test rolling upgrade and rollback sequences with in-flight requests.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] All supported version pairs have an explicit expected outcome.
- [ ] Unsupported combinations fail before execution with stable reason codes.
- [ ] Compatibility claims are generated from passing automated tests.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C030 — Adjacent-layer integration test suite

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `tests/test_integration.py`  
> Tests/evidence: `tests/test_integration.py`  
> Remaining: All adjacent seams (caller tokens, host pipe, observability, control plane) are exercised in-process; the real INV-69 / GAP-09 / INV-71 components are not in this repository.

**Priority:** P0  
**Canonical requirement:** Create automated integration tests proving Fast agent sandbox interoperates with adjacent architectural layers.  
**Current v4.2.0 gap:** No integration tests with INV-69, INV-09, INV-71, GAP-09, or a Wasm layer.

**Target artifacts**
- [ ] `tests/integration/`
- [ ] `tests/fixtures/adjacent/`
- [ ] `evidence/integration/`

### Engineering implementation checklist

- [ ] Create a test harness that can exercise INV-70 through production-like interfaces instead of importing internal helpers only.
- [ ] Add INV-69 integration coverage proving low-risk work is routed to INV-70 with authenticated tenant/workload context, limits, and capabilities intact.
- [ ] Add INV-09 integration coverage proving instruction/profile semantics expected by the portable compute ISA are preserved or explicitly mapped.
- [ ] Add INV-71 integration coverage proving workloads that exceed the fast sandbox policy are rejected/escalated without partial execution or lost correlation IDs.
- [ ] Add GAP-09 integration coverage proving metrics, logs, traces, and termination reasons are exported with required correlation attributes.
- [ ] Add target Wasm-runtime integration coverage proving module validation, instantiation, fuel/memory limits, host imports, and cleanup.
- [ ] Exercise success, policy rejection, invalid artifact, capability denial, deadline, cancellation, dependency timeout, and overload paths for each adjacent layer.
- [ ] Use versioned fixtures/contracts and prevent tests from silently depending on developer-local packages.
- [ ] Run integration tests in a clean isolated CI environment with pinned dependency artifacts.
- [ ] Persist machine-readable JUnit/JSON evidence tied to package and dependency digests.

### Verification and adversarial test checklist

- [ ] Break each adjacent contract intentionally in negative fixtures and verify the suite detects it.
- [ ] Run the integration suite under at least the minimum and maximum supported dependency versions.
- [ ] Verify no integration test is reported as PASS when a required dependency was merely skipped/unavailable.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every declared adjacent dependency has executable interoperability proof.
- [ ] Required integration tests are blocking release gates.
- [ ] Results identify exact versions/digests of all participants.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Implementation & Configuration

## INV-70-C031 — Pinned per-operation Wasm sandbox implementation

> **4.3.0 remediation status: BLOCKED**  
> Implementation: `executor.py::WasmBackend`, `requirements/wasm.lock`, `docs/WASM_RUNTIME.md`, `tests/test_wasm.py`  
> Tests/evidence: `tests/test_wasm.py`  
> Remaining: Engine seam, exact pin, fail-closed behaviour and malicious-module tests are in place; the pinned wasmtime wheel could not be installed in the remediation environment, so 5 engine tests SKIP (and FAIL under INV70_REQUIRE_WASM=1). Wheel hash in wasm.lock is UNSET.

**Priority:** P0  
**Canonical requirement:** Select and pin approved implementations, versions, or specifications for Fast agent sandbox: Per-operation Wasm sandbox.  
**Current v4.2.0 gap:** Checklist requires a pinned per-operation Wasm sandbox implementation/specification; repository contains a custom Python VM and no pinned Wasm runtime.

**Target artifacts**
- [ ] `pyproject.toml or equivalent lock manifest`
- [ ] `wasm/`
- [ ] `wit/`
- [ ] `docs/WASM_RUNTIME.md`
- [ ] `tests/wasm/`

### Engineering implementation checklist

- [ ] Select an approved Wasm runtime/embedding technology through ADR review; document security maintenance, fuel/epoch interruption support, memory limiting, component-model/WIT needs, and supported CPU/OS targets.
- [ ] Pin the runtime binding and native runtime artifacts to exact approved versions/digests in a reproducible dependency lock; prohibit floating ranges for production builds.
- [ ] Define a per-operation instantiation model: validate module/component, create a fresh store/instance, attach resource limiter, bind only approved imports, execute, extract bounded result, and dispose the instance.
- [ ] Disable WASI and ambient capabilities by default; if a WASI feature is required, expose only individually approved preopened resources under policy.
- [ ] Enforce fuel/instruction budget at the Wasm store/runtime layer in addition to any higher-level accounting.
- [ ] Enforce maximum linear memory, table size, globals, module/component byte size, function count where available, and result/host-call payload limits.
- [ ] Add wall-clock preemption using runtime-supported interruption/epoch mechanisms or a killable worker boundary so native guest execution cannot hang indefinitely.
- [ ] Define typed WIT/ABI contracts for run inputs/results and host capabilities; reject malformed or version-incompatible components before instantiation.
- [ ] Bind imported host functions from the authenticated/authorized capability set only; do not expose dynamic name lookup into arbitrary Python objects.
- [ ] Validate all host-call arguments and results against exact schemas and size budgets on both sides of the ABI.
- [ ] Define deterministic trap mapping from Wasm/runtime errors to stable PK_FASTBOX_RESULT reason codes without leaking internal paths or secrets.
- [ ] Decide whether compiled-module caching is allowed; if so, key by cryptographic digest plus runtime/version/config, cap cache size, isolate tenants as required, and never cache mutable trust decisions.
- [ ] Verify module/artifact signature, digest, provenance, and approved version before compilation/instantiation.
- [ ] Define migration/parity tests from the Python reference VM where semantics overlap; clearly mark semantics that intentionally differ.
- [ ] Keep the Python VM out of the production path unless the approved ADR explicitly permits it as a supported profile.
- [ ] Add build reproducibility instructions and a lockfile/runtime-integrity check to CI.

### Verification and adversarial test checklist

- [ ] Run malicious-module tests for infinite loops, memory growth, table abuse, trap storms, oversized imports/exports, invalid modules, and capability probing.
- [ ] Prove a module has no filesystem/network/environment/clock/randomness authority unless the exact capability is granted.
- [ ] Prove fresh-instance state isolation across sequential and concurrent tenant runs.
- [ ] Run runtime-CVE/version policy checks and fail builds when the pinned runtime is unapproved.
- [ ] Benchmark cold instantiate, warm/compiled instantiate, execution, teardown, and memory overhead.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Production runs execute inside the approved pinned Wasm sandbox rather than only the Python VM.
- [ ] All guest resources and wall-clock execution are enforceably bounded outside guest control.
- [ ] No ambient host capability is reachable without explicit authenticated authorization and import binding.
- [ ] Runtime version/digest and module digest are present in release/run evidence.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C035 — Site/environment configuration overlays

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `config.py::resolve`, `docs/CONFIGURATION.md`  
> Tests/evidence: `tests/test_config.py::Overlays`  

**Priority:** P1  
**Canonical requirement:** Support site- and environment-specific configuration without rebuilding immutable artifacts.  
**Current v4.2.0 gap:** No site/environment overlay mechanism independent of rebuilding artifacts.

**Target artifacts**
- [ ] `config/defaults.yaml`
- [ ] `config/inv70.schema.json`
- [ ] `docs/CONFIGURATION.md`

### Engineering implementation checklist

- [ ] Define a typed external configuration schema covering limits, runtime selection, capability policy references, endpoints, telemetry, admission control, and deployment profile.
- [ ] Separate immutable artifact defaults from environment/site overlays so configuration changes do not require rebuilding the package/image.
- [ ] Define deterministic layer precedence, for example compiled safe defaults < environment profile < site overlay < approved workload/tenant policy, while preserving non-overridable security ceilings.
- [ ] Validate the fully merged configuration before activation; reject unknown keys, wrong types, out-of-range values, and unsafe combinations.
- [ ] Define secure loading sources and permissions; do not accept arbitrary guest-controlled configuration paths.
- [ ] Snapshot an immutable effective configuration for each admitted run so hot reload cannot alter semantics mid-execution.
- [ ] Define reload behavior, including whether changes require restart or support validated live activation.
- [ ] Define secret references separately from plaintext configuration and prevent secrets from appearing in diagnostics.
- [ ] Expose effective non-secret configuration version/digest in explain/evidence output.
- [ ] Document configuration examples for dev/test/prod and each supported deployment profile.

### Verification and adversarial test checklist

- [ ] Test merge precedence and hard-ceiling enforcement across conflicting overlays.
- [ ] Test invalid/unknown/unsafe configuration and verify fail-before-activation behavior.
- [ ] Test a concurrent reload while runs are active and prove each run uses one immutable configuration snapshot.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Operational tuning can occur without rebuilding immutable artifacts.
- [ ] Configuration activation is schema-validated and auditable.
- [ ] No lower-scope overlay can weaken non-overridable security ceilings.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C036 — Configuration provenance and activation record

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `config.py::ConfigStore._record`  
> Tests/evidence: `tests/test_config.py::Activation.test_provenance_and_atomicity`  

**Priority:** P1  
**Canonical requirement:** Record configuration provenance, version, author, and activation time.  
**Current v4.2.0 gap:** No configuration provenance record with version, author, source digest, and activation time.

**Target artifacts**
- [ ] `schemas/config-provenance.schema.json`
- [ ] `evidence/config/`
- [ ] `docs/CONFIGURATION.md`

### Engineering implementation checklist

- [ ] Assign every configuration revision a unique config_id and monotonically ordered or content-addressed version.
- [ ] Record source URI/repository, source commit/version, author/automation principal, creation time, approval principal, activation time, and environment/site scope.
- [ ] Canonicalize and hash the effective non-secret configuration; store the digest used by each run/release.
- [ ] Record secret references by opaque identifier/version only, never secret values.
- [ ] Sign or otherwise integrity-protect production configuration manifests before activation.
- [ ] Record predecessor/superseded revision and rollback target.
- [ ] Include schema version and runtime compatibility constraints in the provenance envelope.
- [ ] Emit config_id/config_digest into structured logs, traces, explain output, and release evidence.
- [ ] Keep an append-only activation history sufficient to reconstruct which config was active for an incident window.
- [ ] Define retention and access controls for provenance records.

### Verification and adversarial test checklist

- [ ] Tamper with a stored configuration and prove digest/signature verification rejects activation.
- [ ] Reconstruct the effective configuration metadata for a historical run from run_id plus provenance records.
- [ ] Test rollback and verify the new activation record points to the prior approved revision.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every production run is attributable to one immutable effective configuration digest.
- [ ] Configuration authorship/approval/activation are auditable.
- [ ] Rollback history is complete and tamper-evident enough for incident reconstruction.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C037 — Atomic/transactional configuration activation

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `config.py::ConfigStore.activate/rollback`  
> Tests/evidence: `tests/test_config.py::Activation`  

**Priority:** P0  
**Canonical requirement:** Apply atomic or transactional configuration updates where partial application is unsafe.  
**Current v4.2.0 gap:** No atomic/transactional configuration update mechanism.

**Target artifacts**
- [ ] `docs/CONFIG_TRANSACTION.md`
- [ ] `src or package configuration manager`
- [ ] `tests/config_transaction/`

### Engineering implementation checklist

- [ ] Define which settings must change atomically as one configuration generation (runtime selection, limits, capability policy, trust roots, endpoints, telemetry policy).
- [ ] Implement a stage→validate→prepare→commit activation flow; never mutate live settings field-by-field.
- [ ] Build the complete candidate effective configuration in isolation and run schema, semantic, compatibility, and security validation before commit.
- [ ] Use generation numbers or compare-and-swap semantics to prevent stale writers from overwriting newer configuration.
- [ ] Publish the new immutable configuration snapshot through a single atomic reference/swap for new runs.
- [ ] Keep already admitted runs pinned to their original snapshot unless the documented semantics require cancellation.
- [ ] Define rollback as activation of a previously approved full generation, not ad-hoc reverse edits.
- [ ] For multi-process/node deployment, define quorum/coordination semantics or explicitly scope atomicity to a node and expose rollout generation per node.
- [ ] If partial fleet rollout is allowed, define mixed-generation compatibility and how routing avoids unsafe combinations.
- [ ] Emit activation success/failure events containing old/new generation, digest, actor, and reason.

### Verification and adversarial test checklist

- [ ] Inject failure after every preparation step and prove the prior generation remains fully active.
- [ ] Race concurrent configuration writers and verify stale-generation rejection.
- [ ] Run workloads during activation and prove no run observes a hybrid configuration.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Unsafe partial configuration cannot become externally visible.
- [ ] Every activation is all-or-nothing at the documented scope.
- [ ] Rollback is deterministic, tested, and auditable.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Security, Trust & Isolation

## INV-70-C044 — Node, peer, artifact, provider, and control-plane authentication/attestation

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `security.py::make_attestation/verify_attestation`  
> Tests/evidence: `tests/test_security.py::AttestationTests`  
> Remaining: Verification mechanism for all four roles is implemented and tested; there is no live node/peer/control-plane handshake in this repository to wire it into.

**Priority:** P0  
**Canonical requirement:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.  
**Current v4.2.0 gap:** No node/peer/artifact/provider/control-plane authentication or attestation.

**Target artifacts**
- [ ] `docs/TRUST_MODEL.md`
- [ ] `config/trust-roots.yaml`
- [ ] `schemas/attestation-claims.schema.json`

### Engineering implementation checklist

- [ ] Define distinct identities for node, peer service, executable artifact, capability provider, and control-plane/operator actor.
- [ ] Define trust roots and credential issuers for each identity class and prohibit a credential from one class being accepted as another.
- [ ] Authenticate peer services using workload/service identity before accepting routing, capability, configuration, or telemetry-control messages.
- [ ] Authenticate nodes before enrolling them into a production execution pool.
- [ ] Define attestation requirements for nodes where hardware/software integrity is required; specify required claims, freshness, nonce/challenge, and verifier.
- [ ] Verify artifact identity through digest/signature/provenance before execution, independent of transport authentication.
- [ ] Authenticate capability providers and bind provider identity to the capabilities they are authorized to implement.
- [ ] Authenticate control-plane actors with strong credentials and role binding before configuration, trust-root, policy, or release actions.
- [ ] Define certificate/token/key rotation, revocation, compromise response, and cache invalidation.
- [ ] Bind authenticated peer/node identity into authorization policy and audit context.
- [ ] Define behavior for unknown, expired, revoked, or unverifiable identity/attestation as fail-closed.

### Verification and adversarial test checklist

- [ ] Test impersonation across every identity class and trust-domain boundary.
- [ ] Test stale/replayed attestation evidence and revoked credentials.
- [ ] Test a validly authenticated provider attempting to implement an unauthorized capability.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] No trusted production relationship is established from network location or name alone.
- [ ] Identity/attestation decisions are explicit, versioned, and auditable.
- [ ] Revocation takes effect within a documented bounded interval.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C045 — Executable/policy artifact integrity, provenance, SBOM, and version verification

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `security.py::verify_artifact`, `service.py (wasm path)`  
> Tests/evidence: `tests/test_security.py::ArtifactTests`, `tests/test_integration.py::WasmProfile`  

**Priority:** P0  
**Canonical requirement:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Fast agent sandbox.  
**Current v4.2.0 gap:** No signature, digest, provenance, SBOM, or approved-version verification path for executable/policy artifacts.

**Target artifacts**
- [ ] `docs/ARTIFACT_TRUST.md`
- [ ] `policy/approved-artifacts.yaml`
- [ ] `sbom/`
- [ ] `provenance/`
- [ ] `tools/verify_artifact.py`

### Engineering implementation checklist

- [ ] Define the artifact classes that require verification: Wasm modules/components, runtime packages/native binaries, policy bundles, configuration bundles, schemas, and release packages.
- [ ] Compute and require cryptographic digests for artifacts; identify artifacts by digest rather than mutable tag/path alone.
- [ ] Require an approved digital signature or signed attestation for production artifacts and define accepted issuers/keys.
- [ ] Verify provenance attestation tying artifact digest to source revision, build identity, build workflow, and dependency lock.
- [ ] Generate an SBOM in an approved standard format for the release and retain it with release evidence.
- [ ] Define an allowlist/approval policy for runtime/module/policy versions and reject unapproved or revoked artifacts before execution.
- [ ] Verify signatures/digests before compilation, cache insertion, or policy evaluation so untrusted bytes do not become trusted cache state.
- [ ] Key caches by verified digest and invalidate them when approval/revocation state changes.
- [ ] Define offline verification behavior for edge sites, including cached trust roots and expiry/freshness limits.
- [ ] Record verification result, artifact digest, signer/issuer, provenance digest, and policy version in audit/evidence without leaking sensitive metadata.
- [ ] Integrate dependency/vulnerability scanning results with artifact approval state.

### Verification and adversarial test checklist

- [ ] Test tampered bytes, wrong signer, revoked signer, expired metadata, missing provenance, missing SBOM, and unapproved version.
- [ ] Test cache poisoning attempts where a mutable name points to different content after initial verification.
- [ ] Prove the runtime cannot execute an artifact that lacks required trust evidence in the production profile.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every executable/policy artifact used in production is content-addressed and verified.
- [ ] Verification is fail-closed and occurs before execution/use.
- [ ] Artifact trust evidence is machine-readable and release-correlated.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C048 — Safe behavior when critical trust/time services are unavailable

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `security.py::TrustStore.available/Clock.healthy`, `resilience.py::derive_mode`  
> Tests/evidence: `tests/test_security.py::AuthTests.test_c048_fail_closed`, `tests/test_integration.py::Faults.test_trust_time_audit_outage_halts_then_recovers`  

**Priority:** P0  
**Canonical requirement:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.  
**Current v4.2.0 gap:** No explicit fail-closed behavior for unavailable identity, attestation, policy, key, or time services.

**Target artifacts**
- [ ] `docs/DEPENDENCY_FAILURE_POLICY.md`
- [ ] `config/failure-policy.yaml`
- [ ] `tests/fail_closed/`

### Engineering implementation checklist

- [ ] Classify identity, attestation, policy, key/trust-root, and time services as critical or conditionally cacheable; document the rationale for each.
- [ ] Define production fail-closed behavior for inability to establish caller/workload/node identity or required authorization policy.
- [ ] Define whether previously verified policy/trust material may be cached, its maximum age, revocation assumptions, and the scopes where cached use is permitted.
- [ ] Define trusted-time requirements and use a monotonic clock for local deadlines so wall-clock changes cannot extend execution.
- [ ] Define behavior when wall-clock validity cannot be established for credential/signature expiry; do not silently treat unknown time as valid.
- [ ] Define capability-specific degradation: disable a capability whose identity/key/policy dependency is unavailable rather than enabling it permissively.
- [ ] Define edge/offline exceptions, if any, as explicit signed policy with maximum duration and compensating controls.
- [ ] Distinguish dependency-unavailable, dependency-timeout, invalid-response, and policy-denied reason codes.
- [ ] Emit a security audit event for every fail-closed admission and every use of cached trust material.
- [ ] Document operator recovery steps without including a bypass that disables mandatory verification.

### Verification and adversarial test checklist

- [ ] Fault-inject each critical service as unavailable, slow, stale, and returning malformed data.
- [ ] Move wall clock forward/backward while keeping monotonic time stable and verify deadlines/security decisions remain correct.
- [ ] Expire cached policy/trust material and prove admission transitions to the documented safe state.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Loss of a critical trust dependency never increases privilege.
- [ ] Any cached/offline trust decision is time-bounded, explicit, and auditable.
- [ ] Failure behavior is covered by automated tests and runbooks.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C049 — Tamper-evident security audit event pipeline

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `security.py::AuditLog`  
> Tests/evidence: `tests/test_security.py::AuditTests`, `tests/test_integration.py::Faults.test_audit_sink_failure_is_fail_closed`  

**Priority:** P0  
**Canonical requirement:** Emit tamper-evident audit events for security-sensitive Fast agent sandbox operations.  
**Current v4.2.0 gap:** No tamper-evident/append-only security audit event sink.

**Target artifacts**
- [ ] `schemas/security-audit-event.schema.json`
- [ ] `docs/AUDIT_LOGGING.md`
- [ ] `tools/verify_audit_chain.py`

### Engineering implementation checklist

- [ ] Define a versioned security-audit event schema with event_id, sequence, timestamp, node/site, tenant/workload pseudonymous IDs, run_id, actor/principal, action, object digest, decision, reason code, policy/config/runtime versions, and prior-event hash where applicable.
- [ ] Enumerate mandatory event types: authentication failure, authorization/capability denial, artifact verification, policy decision, trust-root/config change, host-call invocation/denial, sandbox trap classes, emergency override, release/rollback, and audit-pipeline failure.
- [ ] Define canonical serialization before hashing/signing so verification is deterministic.
- [ ] Implement append-only or WORM-capable export; if local buffering is required, bound it and protect integrity across rotation.
- [ ] Hash-chain events or signed batches with sequence numbers to make deletion/reordering/modification detectable at the documented scope.
- [ ] Protect audit signing keys separately from guest/runtime data and define rotation/revocation.
- [ ] Redact secrets, raw guest payloads, tokens, and unnecessary high-cardinality content before persistence.
- [ ] Define behavior when the audit sink is unavailable: buffer within strict limits or fail closed for designated critical operations.
- [ ] Provide an offline verifier that reports chain gaps, signature failures, duplicate sequences, and unsupported schema versions.
- [ ] Correlate audit events to release/config/artifact digests and trace IDs.

### Verification and adversarial test checklist

- [ ] Modify, delete, reorder, duplicate, and splice persisted events and prove verification detects tampering.
- [ ] Fill/disable the audit sink and verify bounded-buffer/fail-closed policy.
- [ ] Run secret-canary tests to prove credentials and guest secrets are not serialized to the audit stream.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Security-sensitive actions create integrity-verifiable events.
- [ ] Tampering is detectable within the stated audit scope.
- [ ] Audit failure semantics are explicit and tested.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Resilience & Failure Handling

## INV-70-C053 — Bounded safe-retry policy with backoff and jitter

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `resilience.py::RetryPolicy`  
> Tests/evidence: `tests/test_resilience.py::Retry`  
> Remaining: Retry is a caller-side policy by design; the sandbox never retries a guest internally.

**Priority:** P1  
**Canonical requirement:** Implement bounded retry with backoff and jitter only where operations are safe to retry.  
**Current v4.2.0 gap:** No retry policy/backoff/jitter implementation or proof that operations are safe to retry.

**Target artifacts**
- [ ] `docs/RETRY_POLICY.md`
- [ ] `config/retry-policy.yaml`
- [ ] `tests/retry/`

### Engineering implementation checklist

- [ ] Inventory every external/adjacent operation and classify it as non-retryable, retryable-idempotent, or retryable-with-idempotency-key.
- [ ] Define transient versus permanent failure classes using stable error codes, not exception string matching.
- [ ] Define maximum attempts, total retry budget, minimum/maximum backoff, and jitter strategy per operation class.
- [ ] Cap retries by the caller/end-to-end deadline so retries cannot outlive the request.
- [ ] Honor dependency retry hints only within local safety and deadline limits.
- [ ] Never retry authentication/authorization/policy denial or malformed input as transient failures.
- [ ] Propagate a stable operation/idempotency key through retried side-effecting host calls.
- [ ] Add retry storm protection and combine retry policy with circuit breaking/admission control.
- [ ] Expose attempt count, accumulated backoff, terminal cause, and dependency identity in telemetry.
- [ ] Document when the stateless guest run itself may be safely retried versus when side effects make replay unsafe.

### Verification and adversarial test checklist

- [ ] Simulate transient failures followed by recovery and prove bounded attempts plus jittered delays.
- [ ] Simulate permanent failure and prove no retry occurs.
- [ ] Run many concurrent failing operations and verify retry synchronization does not create a thundering herd.
- [ ] Prove idempotent duplicate suppression for a retry of a side-effecting host call.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every retryable operation has an explicit safety justification.
- [ ] Retries are bounded by attempt and time budgets.
- [ ] Retry behavior is observable and cannot amplify an outage uncontrollably.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C054 — Admission control, load shedding, and circuit breaking

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `resilience.py::Admission/CircuitBreaker`  
> Tests/evidence: `tests/test_resilience.py::AdmissionBreaker`, `tests/test_integration.py::Faults.test_worker_crash_opens_breaker_then_recovers`  

**Priority:** P0  
**Canonical requirement:** Implement admission control, load shedding, or circuit breaking to prevent Fast agent sandbox failure cascades.  
**Current v4.2.0 gap:** No admission control, concurrency limiter, load shedding, or circuit breaker.

**Target artifacts**
- [ ] `docs/ADMISSION_CONTROL.md`
- [ ] `config/admission.yaml`
- [ ] `tests/overload/`

### Engineering implementation checklist

- [ ] Define hard process/node ceilings for concurrent runs, queued admissions, aggregate guest memory, compiled-module cache, host-call concurrency, and telemetry buffering.
- [ ] Define per-tenant/per-workload quotas so one workload cannot consume all execution slots or memory.
- [ ] Perform admission checks before expensive module compilation/instantiation where possible.
- [ ] Implement bounded semaphores/queues; prohibit unbounded task creation and buffering.
- [ ] Define load-shed priority classes and deterministic overload rejection codes.
- [ ] Implement circuit breakers around failing/slow capability providers or adjacent services with open/half-open/closed behavior and bounded probe concurrency.
- [ ] Combine circuit-breaker state with retry policy to avoid retry amplification.
- [ ] Define recovery hysteresis so the system does not oscillate rapidly between accept/reject states.
- [ ] Expose queue depth, active runs, memory budget usage, rejections, breaker state, and saturation metrics.
- [ ] Define fairness policy across tenants and protect reserved capacity for control/security operations if required.

### Verification and adversarial test checklist

- [ ] Drive the service past CPU/memory/concurrency capacity and verify bounded resource usage plus fast rejection.
- [ ] Saturate one tenant and prove other tenants retain their documented share.
- [ ] Force a provider to fail/timeout and verify breaker transitions and recovery.
- [ ] Run overload for an extended interval and verify queues/caches do not leak or grow unbounded.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Overload cannot create unbounded memory/task growth.
- [ ] Failure of a dependency cannot cascade into unlimited retries/queued work.
- [ ] Admission/load-shed decisions are measurable and reason-coded.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C055 — Failover policy preserving isolation, residency, and consistency

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `resilience.py::select_failover`  
> Tests/evidence: `tests/test_resilience.py::Failover`  
> Remaining: Failover selection policy is implemented and tested; there is no multi-site deployment to exercise it end to end.

**Priority:** P1  
**Canonical requirement:** Define failover behavior without violating isolation, residency, or consistency requirements.  
**Current v4.2.0 gap:** No failover policy across nodes/sites/providers and no residency/isolation constraints for failover.

**Target artifacts**
- [ ] `docs/FAILOVER.md`
- [ ] `config/failover-policy.yaml`
- [ ] `tests/failover/`

### Engineering implementation checklist

- [ ] Define the failover unit: process, node, site, region, provider, or execution tier; mark which are supported.
- [ ] Define RTO/RPO expectations for this stateless sandbox and explicitly identify state that still matters: configuration, policy, trust roots, artifact cache, dedupe/idempotency records, and audit continuity.
- [ ] Define residency/tenant constraints that restrict eligible failover targets before availability is considered.
- [ ] Define trust equivalence requirements for a target node/site: approved runtime, artifact digest, config generation, policy generation, trust roots, and attestation state.
- [ ] Define how in-flight runs are treated on source failure: lost, retried only if safe, or resumed only if an explicit mechanism exists.
- [ ] Define side-effecting host-call behavior so a failed source and replacement target cannot both commit the same effect.
- [ ] Define routing/fencing semantics that prevent stale nodes/controllers from continuing to own work after failover.
- [ ] Define observability/audit continuity so the original attempt and failover attempt share correlation and operation identity.
- [ ] Define recovery/failback rules and compatibility requirements for mixed versions/config generations.
- [ ] Document cases where the correct behavior is no failover because security/residency cannot be preserved.

### Verification and adversarial test checklist

- [ ] Kill a worker/node during guest execution and verify only the documented retry/reject behavior occurs.
- [ ] Partition the control plane and prove stale/fenced nodes cannot accept unauthorized new work.
- [ ] Attempt failover to a disallowed residency/trust domain and verify hard rejection.
- [ ] Fail during a side-effecting host call and verify duplicate-effect protection.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Failover never weakens tenant isolation or residency rules.
- [ ] At-most-once/effectively-once guarantees match the documented host-call contract.
- [ ] Failover/failback procedures are reproducible and tested.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C056 — Defined degraded-operation modes

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `resilience.py::Mode/DEGRADED_RULES`, `service.py::mode`, `RUNBOOK.md#degraded-modes`  
> Tests/evidence: `tests/test_resilience.py::Degraded`, `tests/test_integration.py::Faults`  

**Priority:** P1  
**Canonical requirement:** Provide degraded operation when noncritical dependencies are unavailable.  
**Current v4.2.0 gap:** No defined degraded mode for unavailable noncritical dependencies.

**Target artifacts**
- [ ] `docs/DEGRADED_MODES.md`
- [ ] `config/degraded-mode-policy.yaml`

### Engineering implementation checklist

- [ ] Inventory dependencies and classify each as critical, noncritical, or conditionally cacheable for execution safety.
- [ ] Define named operating modes such as NORMAL, DEGRADED_OBSERVABILITY, DEGRADED_CONTROL_PLANE, OFFLINE_EDGE, and FAIL_CLOSED only where semantics are clear.
- [ ] Define entry/exit conditions for each mode and require hysteresis/health confirmation before returning to NORMAL.
- [ ] Define exactly which operations/capabilities remain available in each degraded mode.
- [ ] Never classify identity, authorization, required artifact verification, or mandatory isolation enforcement as optional degradation unless an approved time-bounded offline policy explicitly covers it.
- [ ] Define bounded local telemetry/audit buffering when exporters are unavailable and behavior when buffers fill.
- [ ] Define cached config/policy use with immutable digest and freshness limits.
- [ ] Expose degraded-mode state in health, metrics, logs, traces, explain output, and release/incident evidence.
- [ ] Define operator actions to intentionally enter/exit a mode and require authenticated audited control.
- [ ] Document user-visible/result semantics so callers can distinguish degraded service from ordinary guest traps.

### Verification and adversarial test checklist

- [ ] Fault-inject every noncritical dependency and verify the expected degraded capability set.
- [ ] Fault-inject a critical security dependency and verify fail-closed admission.
- [ ] Fill local telemetry buffers and verify bounded behavior without guest compromise.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every dependency outage maps to a documented mode or fail-closed result.
- [ ] Degraded operation never silently expands privilege.
- [ ] Mode transitions are observable, audited, and test-covered.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C058 — Duplicate execution and stale-controller protection

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `resilience.py::IdempotencyCache/FencedLease`  
> Tests/evidence: `tests/test_resilience.py::Idempotency`, `tests/test_resilience.py::Fencing`  

**Priority:** P0  
**Canonical requirement:** Protect against split-brain, duplicate ownership, stale controllers, or duplicate execution where relevant.  
**Current v4.2.0 gap:** No duplicate-execution/idempotency protection for side-effecting host callbacks or stale-controller ownership model.

**Target artifacts**
- [ ] `docs/IDEMPOTENCY_AND_FENCING.md`
- [ ] `schemas/operation-id.schema.json`
- [ ] `tests/duplicate_execution/`

### Engineering implementation checklist

- [ ] Define a globally unique operation_id and optional client idempotency_key distinct from run attempt IDs.
- [ ] Define which calls are pure/stateless and which host capabilities may cause externally visible side effects.
- [ ] Require side-effecting capability providers to accept operation identity/idempotency metadata or explicitly declare that automatic replay is forbidden.
- [ ] Define a deduplication record or provider-side idempotency contract with bounded retention consistent with retry/failover windows.
- [ ] Define execution attempt numbering so repeated attempts can be correlated without being mistaken for independent operations.
- [ ] If controllers/routers assign work, implement leases/fencing tokens or generation numbers so stale controllers cannot continue ownership after replacement.
- [ ] Validate fencing/idempotency metadata at the provider/commit boundary, not only in the requester.
- [ ] Define behavior for duplicate requests whose original result is known, unknown, in progress, or expired from dedupe retention.
- [ ] Preserve tenant/workload scope in dedupe keys to prevent cross-tenant collision or information leakage.
- [ ] Audit duplicate suppression, stale-fence rejection, and replay decisions.

### Verification and adversarial test checklist

- [ ] Submit concurrent duplicate requests and verify one effect plus deterministic responses.
- [ ] Crash between host-call request and response, then retry and verify no duplicate effect.
- [ ] Run old/new controller generations concurrently and prove stale fencing tokens are rejected.
- [ ] Test dedupe-record expiry and document the resulting safety boundary.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Side-effecting retries/failovers cannot silently duplicate committed effects within the documented window.
- [ ] Stale owners cannot continue writing after fencing.
- [ ] Duplicate behavior is explicit for every capability class.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C060 — Fault-injection and recovery certification

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `tests/test_integration.py::Faults`  
> Tests/evidence: `tests/test_integration.py::Faults`  
> Remaining: Eight in-process fault-injection scenarios with recovery assertions; certification in a staging environment is still required.

**Priority:** P1  
**Canonical requirement:** Run fault-injection tests proving Fast agent sandbox recovery against documented objectives.  
**Current v4.2.0 gap:** No fault-injection harness/results for dependency/process/node/site/control-plane recovery objectives.

**Target artifacts**
- [ ] `tests/fault_injection/`
- [ ] `docs/RECOVERY_OBJECTIVES.md`
- [ ] `evidence/fault-injection/`

### Engineering implementation checklist

- [ ] Define failure domains and expected recovery objectives for process, worker, node, site, control plane, identity, policy, trust/key, telemetry, configuration, artifact store/cache, and capability provider failures.
- [ ] Build deterministic fault hooks or harness controls rather than relying only on accidental failures.
- [ ] Inject host-call timeout, exception, hung callback, malformed return, cancellation, and process termination.
- [ ] Inject Wasm runtime/module validation failure, memory exhaustion, fuel exhaustion, interruption, and runtime crash where the embedding permits.
- [ ] Inject configuration update failure before and after prepare/commit points.
- [ ] Inject network partition and delayed/reordered dependency responses at integration boundaries.
- [ ] Inject trust/identity/policy unavailability and verify fail-closed/degraded rules.
- [ ] Inject telemetry/audit exporter outage and buffer saturation.
- [ ] Measure recovery time, dropped/duplicated operations, residual resource usage, queue drain, and error-rate normalization.
- [ ] Persist test seed/scenario, environment manifest, versions/digests, timeline, and observed objective values.

### Verification and adversarial test checklist

- [ ] Re-run each scenario repeatedly and require deterministic safety invariants even when timing varies.
- [ ] Assert no cross-tenant state/capability leakage after recovery.
- [ ] Assert no orphan processes/instances/tasks/resources remain after injected failures.
- [ ] Compare measured recovery objectives to approved thresholds and fail certification on regression.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every documented critical failure mode has an automated injection scenario.
- [ ] Recovery objectives have machine-readable measurements, not narrative-only claims.
- [ ] Fault-injection results are part of release evidence for production certification.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Performance & Resource Efficiency

## INV-70-C061 — Reproducible performance and resource baseline

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `tools/bench.py`, `perf/baseline.json`  
> Tests/evidence: `tests/test_governance.py::Perf`  
> Remaining: Baseline is for one machine class (recorded in the file).

**Priority:** P1  
**Canonical requirement:** Establish reproducible baselines for Fast agent sandbox latency, throughput, startup, CPU, memory, storage, network, and power overhead.  
**Current v4.2.0 gap:** No reproducible benchmark baseline artifact for latency, throughput, startup, CPU, memory, storage, network, or power.

**Target artifacts**
- [ ] `benchmarks/`
- [ ] `benchmarks/baselines/`
- [ ] `docs/BENCHMARKING.md`

### Engineering implementation checklist

- [ ] Define benchmark environment manifests containing CPU model/architecture, cores, memory, OS/kernel, Python version, Wasm runtime/version, power mode, dependency versions, and relevant configuration digests.
- [ ] Define representative workload classes: tiny arithmetic/transform, branch-heavy, memory-near-limit, hostcall-free, hostcall-light, and hostcall-dominated.
- [ ] Measure cold startup/instantiate and warm startup separately.
- [ ] Measure end-to-end latency distributions including p50/p95/p99/p99.9 where sample size supports them.
- [ ] Measure throughput at fixed concurrency levels and saturation point.
- [ ] Measure CPU time, process RSS/peak memory, guest logical/linear memory, compiled-cache footprint, temporary allocation, and file/image/package footprint where relevant.
- [ ] Measure host-call overhead and serialization/copy cost separately from guest execution.
- [ ] Measure network bytes/requests when remote providers or telemetry are enabled; report zero/not-applicable explicitly for local-only paths.
- [ ] Define power/energy methodology or mark power as a separate edge-specific benchmark linked to C068.
- [ ] Use warmups, fixed seeds/data, repeated trials, robust statistics, and machine-readable raw results.
- [ ] Keep baseline files immutable per release/hardware profile and include commit/artifact/config digests.

### Verification and adversarial test checklist

- [ ] Run the same benchmark twice on the same profile and quantify expected variance.
- [ ] Validate benchmark scripts run from a clean checkout/environment using pinned dependencies.
- [ ] Check for accidental benchmark bypass/skips and fail if required metrics are missing.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] A release has reproducible baseline data for all checklist resource dimensions or an explicit justified N/A.
- [ ] Baseline data identifies the exact software/config/hardware profile.
- [ ] Raw and summarized measurements are retained for later regression comparison.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C063 — Steady, burst, overload, scale, and recovery performance suite

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `tools/bench.py::bench_service/bench_burst`  
> Tests/evidence: `perf/baseline.json`  
> Remaining: Steady, burst, overload and recovery measured; multi-node scale not measurable here.

**Priority:** P1  
**Canonical requirement:** Measure Fast agent sandbox under steady load, burst load, overload, scale-out, scale-in, and recovery.  
**Current v4.2.0 gap:** No steady/burst/overload/scale-out/scale-in/recovery performance suite.

**Target artifacts**
- [ ] `benchmarks/scenarios/`
- [ ] `evidence/performance-scenarios/`

### Engineering implementation checklist

- [ ] Define a steady-state scenario at representative utilization long enough to observe stable latency/resource behavior.
- [ ] Define burst scenarios with rapid concurrency arrival and realistic request size distributions.
- [ ] Define overload scenarios exceeding admission, CPU, host-provider, and memory capacity to measure rejection and collapse behavior.
- [ ] Define scale-out scenarios adding workers/nodes while load is active and measure convergence plus routing fairness.
- [ ] Define scale-in scenarios draining/removing workers without dropping or duplicating accepted work.
- [ ] Define recovery scenarios where a saturated or failed dependency becomes healthy and measure queue drain/circuit recovery.
- [ ] Record rate, errors, latency distributions, saturation, queue/backlog, memory, CPU, cache behavior, and dependency metrics for every phase.
- [ ] Segment results by tenant/workload and operation class so aggregate metrics cannot hide starvation.
- [ ] Define pass/fail thresholds or regression budgets per scenario and hardware/deployment profile.
- [ ] Automate scenario execution and machine-readable result comparison in performance CI.

### Verification and adversarial test checklist

- [ ] Repeat burst/overload scenarios with randomized arrival timing and ensure safety limits remain invariant.
- [ ] Check recovery returns metrics/resource usage near baseline and leaves no growing backlog/leak.
- [ ] Validate scale-in never terminates admitted work contrary to the lifecycle contract.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] All six required load phases have repeatable automated evidence.
- [ ] Overload produces controlled shedding rather than unbounded degradation.
- [ ] Recovery and scaling behavior meet approved objectives.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C064 — Per-workload and per-tenant overhead measurement

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `tools/bench.py::bench_tenants`  
> Tests/evidence: `perf/baseline.json`  

**Priority:** P2  
**Canonical requirement:** Measure per-workload and per-tenant overhead introduced by Fast agent sandbox.  
**Current v4.2.0 gap:** No per-workload/per-tenant overhead measurements.

**Target artifacts**
- [ ] `benchmarks/overhead/`
- [ ] `docs/OVERHEAD_MODEL.md`

### Engineering implementation checklist

- [ ] Define a direct/native reference path or minimal baseline appropriate for each workload class so sandbox overhead can be separated from work cost.
- [ ] Measure Python-reference VM overhead and target Wasm sandbox overhead separately during migration.
- [ ] Measure fixed per-run costs: validation, authentication/authorization, artifact verification/cache lookup, instantiate/start, telemetry, cleanup.
- [ ] Measure variable per-instruction/operation costs and host-call boundary costs.
- [ ] Measure per-tenant isolation/accounting overhead with 1, 2, N concurrent tenants under equal and skewed load.
- [ ] Measure memory retained per active tenant/workload, including caches, queues, identity/policy context, and metrics cardinality.
- [ ] Measure fairness and noisy-neighbor effects under one abusive/high-load tenant.
- [ ] Segment overhead by cold/warm artifact cache and local/remote capability provider.
- [ ] Record overhead as absolute values and percentage/delta relative to the selected baseline.
- [ ] Define acceptable overhead budgets by supported deployment profile.

### Verification and adversarial test checklist

- [ ] Run overhead benchmarks with identical workload payload/seed across compared paths.
- [ ] Verify tenant tagging itself does not cause unbounded metrics/log cardinality.
- [ ] Prove per-tenant quotas/fairness controls prevent one tenant from materially invalidating others’ measured SLOs beyond policy.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Per-workload and per-tenant overhead is quantified rather than inferred.
- [ ] Results separate sandbox overhead from provider/network work.
- [ ] Approved overhead budgets feed release regression gates.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C065 — Serialization/copy/context-switch/network-hop/state duplication analysis

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `docs/PERFORMANCE.md#overhead-analysis`  
> Tests/evidence: `perf/baseline.json`  

**Priority:** P2  
**Canonical requirement:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Fast agent sandbox.  
**Current v4.2.0 gap:** No serialization/copy/context-switch/network-hop/image/state duplication analysis.

**Target artifacts**
- [ ] `docs/DATA_PATH_ANALYSIS.md`
- [ ] `profiles/`
- [ ] `benchmarks/data-path/`

### Engineering implementation checklist

- [ ] Draw the end-to-end data path from INV-69 caller through authentication/admission, artifact loading, Wasm ABI, host capability calls, result serialization, and observability export.
- [ ] For each edge, identify representation and ownership: Python object, bytes, Wasm linear memory, RPC payload, log/trace event, cache entry.
- [ ] Count serialization/deserialization steps and identify duplicate encoding of the same payload.
- [ ] Identify large memory copies across Python↔Wasm, process IPC, RPC, telemetry, and cache boundaries.
- [ ] Count process/thread/task context switches on the hot path using an approved profiler where available.
- [ ] Count network hops and distinguish mandatory trust boundaries from avoidable proxy/routing hops.
- [ ] Inventory duplicated module images, compiled artifacts, policy/config snapshots, and dedupe state per process/node/tenant.
- [ ] Profile allocation hotspots, peak temporary memory, and GC pressure for representative payload sizes.
- [ ] Quantify the cost of every identified duplication/hop before proposing optimization.
- [ ] Mark copies/hops that are security/isolation requirements and therefore must not be removed merely for speed.

### Verification and adversarial test checklist

- [ ] Capture reproducible profiles/traces for cold and warm representative runs.
- [ ] Use payload-size sweeps to identify nonlinear copying/serialization behavior.
- [ ] Validate profile annotations against source-level instrumentation and benchmark deltas.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every major data-path copy, serialization boundary, context switch, network hop, and duplicated state store is documented.
- [ ] Optimization candidates are ranked by measured cost and semantic risk.
- [ ] Security-mandated boundaries are explicitly protected from unsafe optimization.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C066 — Measured locality/caching/batching/zero-copy optimizations

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `executor.py::ProcessExecutor(warm)`, `docs/PERFORMANCE.md#optimizations`  
> Tests/evidence: `perf/baseline.json#warm_vs_cold`  

**Priority:** P2  
**Canonical requirement:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.  
**Current v4.2.0 gap:** No documented or measured locality/caching/direct-composition/batching/zero-copy/kernel-bypass optimization work.

**Target artifacts**
- [ ] `docs/PERFORMANCE_OPTIMIZATIONS.md`
- [ ] `benchmarks/optimization/`

### Engineering implementation checklist

- [ ] Use C065 measurements to select only optimizations with quantified material impact.
- [ ] Prefer execution on a node/site that already has the verified module/runtime artifacts when residency/security policy permits.
- [ ] Cache validated/compiled Wasm artifacts by immutable digest plus runtime/compiler/config key; bound size and eviction, and recheck approval/revocation before use.
- [ ] Avoid reserializing immutable request metadata across layers by defining a stable typed envelope.
- [ ] Evaluate direct composition between INV-69 and INV-70 when it removes a hop without collapsing an intended trust/isolation boundary.
- [ ] Evaluate batching only for operations whose lifecycle, cancellation, tenant isolation, deadlines, and error attribution remain independent.
- [ ] Evaluate zero-copy or shared-buffer techniques for large byte payloads only when ownership/lifetime and cross-tenant isolation can be proven.
- [ ] Avoid duplicated per-run state by referencing immutable config/policy/artifact digests instead of copying large structures.
- [ ] Evaluate kernel-bypass or specialized I/O only for proven network bottlenecks and only where deployment support/operational complexity are justified.
- [ ] Document semantic invariants for every optimization and retain a safe fallback path where appropriate.
- [ ] Remeasure latency/throughput/CPU/memory after each optimization and quantify regression elsewhere.

### Verification and adversarial test checklist

- [ ] Run equivalence/property tests comparing optimized and unoptimized paths.
- [ ] Run tenant-isolation/security tests specifically against caches/shared buffers/batched paths.
- [ ] Benchmark before/after with identical environment and confidence/variance reporting.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Each enabled optimization has measured benefit and no loss of security/correctness semantics.
- [ ] Caches and shared resources are bounded and content-addressed.
- [ ] Optimization results are incorporated into the performance baseline and release gate.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C068 — Edge-node power and thermal characterization

> **4.3.0 remediation status: BLOCKED**  
> Implementation: `docs/PERFORMANCE.md#edge-power`  
> Tests/evidence: —  
> Remaining: Needs physical edge hardware with power instrumentation; procedure is written, no measurements exist.

**Priority:** P2  
**Canonical requirement:** Measure power and thermal impact on constrained edge nodes where relevant.  
**Current v4.2.0 gap:** No edge-node power/thermal measurement methodology or results.

**Target artifacts**
- [ ] `benchmarks/edge-power/`
- [ ] `docs/EDGE_POWER_THERMAL.md`

### Engineering implementation checklist

- [ ] Define which near-edge/far-edge profiles require power/thermal certification and which are not applicable.
- [ ] Define representative edge hardware classes and record CPU/SoC, cooling mode, power profile, battery/external power state, OS/kernel, and ambient conditions where measurable.
- [ ] Measure idle baseline, sandbox startup energy, energy per operation, sustained watts under steady load, and burst power where tooling supports it.
- [ ] Record package/SoC temperature, thermal throttling indicators, effective CPU frequency, and performance degradation over sustained runs.
- [ ] Use platform counters such as RAPL or vendor/OS energy APIs where validated; otherwise document calibrated external measurement methodology.
- [ ] Separate guest execution energy from remote network/provider energy where only local measurement is available.
- [ ] Measure impact of compiled-module caching, telemetry level, concurrency, and admission limits on power/thermal behavior.
- [ ] Define thermal/power guardrails or admission reductions for constrained nodes if required by the deployment profile.
- [ ] Capture raw samples and synchronized workload timeline for reproducibility.
- [ ] Document measurement uncertainty and unavailable sensors instead of fabricating precision.

### Verification and adversarial test checklist

- [ ] Repeat measurements after thermal stabilization and across multiple trials.
- [ ] Run sustained/soak load long enough to expose throttling behavior for the selected hardware profile.
- [ ] Verify any power-aware load shedding preserves tenant/security policies.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every edge profile marked relevant has measured power/thermal evidence or a documented unsupported status.
- [ ] Thermal throttling impact on latency/throughput is quantified.
- [ ] Power metrics can be compared release-over-release on the same hardware class.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C070 — Blocking performance-regression release gate

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `tools/bench.py::gate`, `.github/workflows/ci.yml`  
> Tests/evidence: `tests/test_governance.py::Perf`  

**Priority:** P1  
**Canonical requirement:** Block releases that regress approved Fast agent sandbox startup, density, throughput, or tail-latency thresholds.  
**Current v4.2.0 gap:** No benchmark gate that blocks releases on startup/density/throughput/tail-latency regression.

**Target artifacts**
- [ ] `performance_budget.yaml`
- [ ] `tools/check_performance_regression.py`
- [ ] `evidence/performance-gate.json`

### Engineering implementation checklist

- [ ] Define approved thresholds/budgets for cold/warm startup, density/concurrency, throughput, p95/p99/tail latency, CPU, and memory for each certified hardware/deployment profile.
- [ ] Derive thresholds from C061/C063/C064 baselines and record the approving owner plus effective release.
- [ ] Define statistically robust comparison rules including minimum sample size, warmup, variance handling, allowed regression, and noise quarantine process.
- [ ] Compare candidates only against a compatible hardware/software benchmark profile; never mix incomparable runners silently.
- [ ] Fail closed when required benchmark data is missing, stale, skipped, or collected on an unapproved environment.
- [ ] Store candidate/baseline raw data and summary digests in machine-readable evidence.
- [ ] Allow threshold exceptions only through the formal waiver mechanism with owner, rationale, compensating control, and expiry.
- [ ] Gate both absolute SLO limits and relative regressions where appropriate.
- [ ] Add a local/reproducible command developers can run before CI.
- [ ] Publish gate reason codes identifying exactly which metric/profile caused failure.

### Verification and adversarial test checklist

- [ ] Inject synthetic regressions into benchmark output and verify the gate blocks release.
- [ ] Inject missing/skipped/stale baseline data and verify failure rather than pass.
- [ ] Test approved temporary waiver expiry and verify an expired waiver no longer bypasses the gate.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Production release cannot proceed with an unapproved startup/density/throughput/tail-latency regression.
- [ ] Gate decisions are reproducible from stored data/configuration.
- [ ] All bypasses are explicit, owner-approved, time-bounded, and auditable.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Observability & Explainability

## INV-70-C072 — Runtime structured metrics implementation

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `telemetry.py::Metrics`  
> Tests/evidence: `tests/test_telemetry.py::MetricsTests`  

**Priority:** P0  
**Canonical requirement:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.  
**Current v4.2.0 gap:** Counters/histogram names are declared but runtime emits no metrics for rate/errors/latency/saturation/backlog/resource use.

**Target artifacts**
- [ ] `observability/metrics.py or equivalent`
- [ ] `docs/METRICS.md`
- [ ] `tests/observability/test_metrics.py`

### Engineering implementation checklist

- [ ] Implement the currently declared signals (runs, terminations by reason, fuel_used) rather than leaving them as contract-only names.
- [ ] Add run duration/startup/instantiate histograms and host-call duration histograms using stable units.
- [ ] Add counters for admission accepted/rejected, authentication/authorization failures, capability denied, artifact verification failures, cancellations, deadlines, and internal faults.
- [ ] Add gauges/up-down counters for active runs, queued admissions, active host calls, memory budget usage, compiled-cache size, and telemetry/audit buffer depth.
- [ ] Add saturation metrics for concurrency limits, queue limits, provider circuit breakers, and per-tenant quota rejection.
- [ ] Define metric naming/versioning conventions and avoid renaming semantics without compatibility policy.
- [ ] Define safe low-cardinality attributes such as component, result class, capability class, deployment profile, runtime version; do not put raw tenant IDs/run IDs in metric labels.
- [ ] Expose tenant/workload aggregation only through bounded/approved cardinality strategy.
- [ ] Provide an exporter abstraction compatible with the selected observability stack and define behavior when export is unavailable.
- [ ] Record runtime/module/config/artifact version dimensions where cardinality remains bounded and operationally useful.

### Verification and adversarial test checklist

- [ ] Unit-test metric increments/observations for every major success/failure path.
- [ ] Run cardinality tests with many tenants/operations and prove label sets remain bounded.
- [ ] Fault the exporter and verify guest execution semantics follow the degraded-mode policy without blocking indefinitely.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Rate, errors, latency, saturation, backlog, and resource use are all observable from emitted metrics.
- [ ] Metric schema/cardinality is documented and test-enforced.
- [ ] Metrics are included in integration and dashboard certification.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C073 — Structured logging with stable correlation identifiers

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `telemetry.py::StructuredLog`  
> Tests/evidence: `tests/test_telemetry.py::LogTests`  

**Priority:** P0  
**Canonical requirement:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.  
**Current v4.2.0 gap:** No structured logging with stable node/tenant/workload/component/operation identifiers.

**Target artifacts**
- [ ] `observability/logging.py or equivalent`
- [ ] `docs/LOGGING.md`
- [ ] `schemas/log-event.schema.json`

### Engineering implementation checklist

- [ ] Adopt structured JSON or equivalent typed log events; prohibit security-relevant parsing of free-form message text.
- [ ] Define stable fields including event_schema, timestamp, severity, event_code, component=INV-70, node_id, site/environment, tenant_id/workload_id in privacy-safe form, operation_id, run_id, attempt, trace_id/span_id, config_digest, runtime_version, and result_reason.
- [ ] Generate operation/run identifiers outside guest control and validate any caller-supplied correlation value before use.
- [ ] Define event codes for admission, validation, runtime start/finish, host-call start/finish/deny, trap classes, config activation, artifact verification, and degraded/failure modes.
- [ ] Never log guest program/payload, capability arguments/results, secrets, tokens, raw credentials, or host exception messages by default.
- [ ] Implement field-level redaction/allowlisting rather than regex-only postprocessing.
- [ ] Normalize errors to stable reason codes and optionally safe exception class names.
- [ ] Define log levels and sampling rules; security/audit events must not be accidentally sampled like debug noise.
- [ ] Bound individual log event size and truncate/hash only according to documented rules.
- [ ] Propagate correlation fields across adjacent layer and host-call boundaries.

### Verification and adversarial test checklist

- [ ] Use canary secrets/tokens in inputs and assert they do not appear in emitted logs.
- [ ] Test malformed/newline/control-character capability names/identifiers against log-injection defenses.
- [ ] Validate every log event against the schema in tests and sample production pipelines.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Operators can correlate a run across components without inspecting guest payloads.
- [ ] Logging is structured, bounded, privacy-aware, and schema-versioned.
- [ ] Security-relevant decisions use stable event/reason codes.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C074 — Distributed trace-context propagation

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `telemetry.py::TraceContext`  
> Tests/evidence: `tests/test_telemetry.py::TraceTests`, `tests/test_integration.py::Observability.test_trace_propagates`  

**Priority:** P1  
**Canonical requirement:** Propagate trace context across all relevant Fast agent sandbox boundaries.  
**Current v4.2.0 gap:** No trace-context input/output propagation.

**Target artifacts**
- [ ] `docs/TRACING.md`
- [ ] `observability/tracing.py or equivalent`
- [ ] `tests/observability/test_tracing.py`

### Engineering implementation checklist

- [ ] Adopt a standard trace-context representation at external boundaries and define accepted header/envelope fields.
- [ ] Validate incoming trace context and treat it only as correlation metadata, never as authenticated identity/authorization.
- [ ] Create an INV-70 run span covering admission through terminal result with bounded attributes.
- [ ] Create child spans for artifact verification/cache, Wasm validation/instantiate, guest execute, and each host capability call where useful.
- [ ] Propagate context to adjacent layers/capability providers and accept returned context according to the protocol.
- [ ] Generate new context when none is supplied and prevent guest code from forging parentage used for security decisions.
- [ ] Attach operation_id/run_id, result class, runtime/config/artifact digests, deployment profile, and capability name/class using cardinality/privacy policy.
- [ ] Define sampling behavior and ensure security/audit events are not dependent on trace sampling.
- [ ] Define trace behavior across retries/failover: preserve logical operation correlation while creating distinct attempt spans.
- [ ] Bound span events/attributes and sanitize exception data.

### Verification and adversarial test checklist

- [ ] Integration-test parent/child relationships across INV-69→INV-70→capability provider/GAP-09.
- [ ] Test malformed trace context and verify safe rejection/regeneration without execution failure.
- [ ] Test retries/failover and verify one logical operation can be reconstructed from spans.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Relevant boundaries propagate trace context consistently.
- [ ] Tracing cannot alter authentication/authorization semantics.
- [ ] Trace data complies with telemetry privacy/cardinality policy.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C075 — Safe high-cardinality diagnostic channel

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `telemetry.py::DiagnosticChannel`  
> Tests/evidence: `tests/test_telemetry.py::DiagTests`  

**Priority:** P1  
**Canonical requirement:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.  
**Current v4.2.0 gap:** No safe high-cardinality diagnostic channel; redacting host exception messages is only a narrow safeguard.

**Target artifacts**
- [ ] `docs/DIAGNOSTICS.md`
- [ ] `schemas/diagnostic-event.schema.json`
- [ ] `tests/observability/test_diagnostics.py`

### Engineering implementation checklist

- [ ] Separate high-cardinality diagnostics from ordinary metrics and default production logs.
- [ ] Define role-based/attribute-based authorization for enabling or retrieving diagnostic detail.
- [ ] Define an allowlist of diagnostic fields; exclude raw secrets, credentials, unbounded guest payloads, and sensitive host-call content by default.
- [ ] Pseudonymize/hash tenant/workload identifiers where raw identifiers are not operationally required.
- [ ] Rate-limit and byte-limit diagnostic emission per node/tenant/run to prevent attacker-driven storage or CPU amplification.
- [ ] Define short retention and automatic expiry for high-cardinality captures unless incident hold is explicitly authorized.
- [ ] Bind diagnostic captures to operation/run/trace IDs and release/config/artifact digests.
- [ ] Implement an explicit diagnostic session/capture ID with owner, purpose, start/end time, and audit trail.
- [ ] Define safe stack/exception capture that excludes host locals/environment/secrets.
- [ ] Provide a redaction scanner/canary test corpus for tokens, keys, PII-like values, and guest secrets.

### Verification and adversarial test checklist

- [ ] Attempt to exfiltrate secrets through guest values, host exceptions, capability names, and diagnostic metadata.
- [ ] Flood diagnostic events and prove rate/size/retention limits.
- [ ] Test unauthorized diagnostic enable/read operations and require security audit events.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Operators can obtain per-run diagnostic detail without exploding metric cardinality or leaking secrets.
- [ ] Diagnostic access and capture are time-bounded and audited.
- [ ] Privacy/redaction tests are blocking.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C077 — Operator-readable explain view

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `service.py::Sandbox.explain`  
> Tests/evidence: `tests/test_integration.py::Observability`  

**Priority:** P1  
**Canonical requirement:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.  
**Current v4.2.0 gap:** No operator-readable explain view.

**Target artifacts**
- [ ] `schemas/explain-run.schema.json`
- [ ] `tools/inv70_explain.py`
- [ ] `docs/EXPLAINABILITY.md`

### Engineering implementation checklist

- [ ] Define a machine-readable explain record keyed by operation_id/run_id.
- [ ] Include admission decision, authenticated principal class, tenant/workload context, deployment profile, effective limits, capability grants/denials, and policy/config versions.
- [ ] Include artifact/module digest and verification outcome, selected runtime/version, and relevant compatibility negotiation result.
- [ ] Include lifecycle state timeline and terminal reason code.
- [ ] Include host capability calls by capability name/class, duration/status, and safe provider identity; exclude sensitive arguments/results.
- [ ] Include key constraint decisions such as residency/failover/degraded-mode/precedence outcomes and the rule/reason that controlled them.
- [ ] Link to trace ID, security-audit event IDs, release lineage, and live infrastructure identifiers where available.
- [ ] Provide both JSON and human-readable CLI/text rendering from the same source record.
- [ ] Define field-level authorization/redaction so one tenant cannot inspect another tenant’s details.
- [ ] Ensure explain generation is observational and cannot mutate or replay execution.

### Verification and adversarial test checklist

- [ ] Create golden explain records for success, capability denial, invalid artifact, fuel exhaustion, deadline, overload, and dependency failure.
- [ ] Compare explain output against logs/traces/audit evidence for consistency.
- [ ] Run secret-canary and cross-tenant authorization tests against explain retrieval.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] An operator can answer why a run was admitted/rejected/terminated from one correlated view.
- [ ] Every decision shown is linked to versioned inputs/policy rather than inferred post hoc.
- [ ] Explain output is privacy-safe and schema-versioned.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C078 — Correlation to release lineage and live infrastructure graph

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `service.py::RELEASE_LINEAGE`  
> Tests/evidence: `tests/test_integration.py::Observability`  
> Remaining: Every run links to release version, source revision and config digest; no live infrastructure graph exists to correlate against.

**Priority:** P1  
**Canonical requirement:** Correlate Fast agent sandbox events with application release lineage and the live infrastructure graph.  
**Current v4.2.0 gap:** No correlation with release lineage or live infrastructure graph.

**Target artifacts**
- [ ] `schemas/lineage-context.schema.json`
- [ ] `docs/LINEAGE.md`
- [ ] `observability/lineage.py or equivalent`

### Engineering implementation checklist

- [ ] Define immutable release identifiers: package version, source commit, build/provenance digest, package/image digest, SBOM digest, and runtime dependency lock digest.
- [ ] Define live infrastructure identifiers: node, site, environment, deployment profile, worker/process generation, and control-plane/routing generation where applicable.
- [ ] Define workload identifiers from authenticated orchestration context rather than guest-supplied labels.
- [ ] Attach release/infrastructure lineage fields to run logs, trace spans, explain records, and security audit events.
- [ ] Expose the currently running release/config/runtime/artifact digests through a health/info endpoint or diagnostic API.
- [ ] Integrate with the live infrastructure graph/CMDB mechanism through a typed adapter; do not hardcode environment-specific endpoints in runtime.py.
- [ ] Define behavior when graph/CMDB is unavailable: execution may continue only according to degraded-mode policy, while lineage fields from local immutable metadata remain available.
- [ ] Correlate failover/retry attempts to both source and destination node/site generations.
- [ ] Preserve historical lineage long enough to reconstruct incidents after rolling upgrades.
- [ ] Define privacy boundaries for tenant/workload lineage fields.

### Verification and adversarial test checklist

- [ ] Deploy two release/config generations concurrently and prove telemetry can distinguish them.
- [ ] Perform rolling upgrade/failover and reconstruct the exact execution node/release/config for each attempt.
- [ ] Fault the graph adapter and verify no incorrect fabricated topology metadata is emitted.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every production run can be tied to exact release/config/runtime/artifact and infrastructure identity.
- [ ] Lineage is consistent across metrics/logs/traces/audit/explain where applicable.
- [ ] Historical incident reconstruction does not depend on mutable “latest” labels.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C079 — Telemetry retention, sampling, privacy, and export policy

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `telemetry.py::TELEMETRY_POLICY/redact`  
> Tests/evidence: `tests/test_telemetry.py`  
> Remaining: Policy as code with in-process redaction, sampling and bounds; retention-day enforcement belongs to the collector (GAP-09).

**Priority:** P1  
**Canonical requirement:** Define telemetry retention, sampling, privacy, and export policy.  
**Current v4.2.0 gap:** No telemetry retention/sampling/privacy/export policy.

**Target artifacts**
- [ ] `docs/TELEMETRY_POLICY.md`
- [ ] `config/telemetry-policy.yaml`
- [ ] `schemas/telemetry-policy.schema.json`

### Engineering implementation checklist

- [ ] Classify each telemetry class: metrics, operational logs, security audit, traces, high-cardinality diagnostics, benchmark evidence, and release evidence.
- [ ] Define data classification for identifiers, artifact digests, tenant/workload metadata, capability names, error details, and any potentially sensitive fields.
- [ ] Define retention period and storage class per telemetry type; keep security/audit requirements distinct from transient debug data.
- [ ] Define sampling rules for traces/logs and explicitly identify unsampled mandatory security/audit events.
- [ ] Define export destinations, protocols, encryption-in-transit, tenant partitioning, and cross-region/residency restrictions.
- [ ] Define access control and purpose restrictions for high-cardinality/tenant-specific telemetry.
- [ ] Define local buffering limits, encryption-at-rest where used, overflow behavior, and deletion after successful export.
- [ ] Define deletion/expiry workflow and legal/incident hold interaction where applicable.
- [ ] Define redaction/allowlisting rules before data leaves the node/process.
- [ ] Version and sign/approve telemetry policy like other production configuration and expose its digest in explain/evidence.

### Verification and adversarial test checklist

- [ ] Run schema/policy tests demonstrating required fields are retained while prohibited fields are dropped/redacted.
- [ ] Test export to a disallowed residency destination and require rejection.
- [ ] Test sampling rates and confirm mandatory security events are never accidentally sampled out.
- [ ] Test retention/expiry on synthetic records.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Telemetry handling is explicit for retention, privacy, sampling, and export.
- [ ] No telemetry class relies on indefinite/default storage behavior.
- [ ] Policy is machine-readable, versioned, and enforced by tests.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C080 — Operational dashboards, alerts, and diagnostic classification

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `ops/alerts.yaml`, `ops/dashboard.json`, `service.py::REASON_CODES`  
> Tests/evidence: `tests/test_governance.py::Ops`  
> Remaining: Alert rules, dashboard and diagnostic classes are shipped as code; not deployed to a monitoring stack.

**Priority:** P1  
**Canonical requirement:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.  
**Current v4.2.0 gap:** No dashboards or alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defects.

**Target artifacts**
- [ ] `observability/dashboards/`
- [ ] `observability/alerts/`
- [ ] `docs/runbooks/`

### Engineering implementation checklist

- [ ] Create dashboards for request rate, acceptance/rejection, success/trap/error rate, latency distributions, active/queued work, fuel/memory use, host-call latency/errors, and runtime/cache health.
- [ ] Create explicit panels/queries separating ordinary load/saturation from software errors.
- [ ] Create policy/security panels for authentication failure, capability denial, invalid/unapproved artifact, attestation failure, and fail-closed dependency events.
- [ ] Create dependency panels for capability-provider, identity, policy, trust/key, telemetry, and control-plane failures.
- [ ] Create overload panels for queue depth, admission shed, quota rejection, circuit-breaker state, and retry volume.
- [ ] Create release/config comparison panels to spot regressions correlated with rollout generation.
- [ ] Define alerts for SLO burn, sustained saturation, abnormal trap/internal-error rate, audit pipeline failure, security anomaly, dependency outage, and performance-regression indicators.
- [ ] Define alert severity, threshold rationale, minimum duration/hysteresis, routing owner, and runbook URL.
- [ ] Avoid alerting on raw high-cardinality labels; aggregate safely by service/site/profile/reason class.
- [ ] Create runbooks that tell responders how to distinguish load, policy rejection, dependency failure, attack indicators, and software defects before remediation.

### Verification and adversarial test checklist

- [ ] Use synthetic telemetry to trigger every alert and verify routing/runbook linkage.
- [ ] Replay representative incidents and verify dashboards expose enough evidence to classify the failure correctly.
- [ ] Test alert suppression/hysteresis during known overload recovery to prevent flapping without masking persistent failures.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Each required failure class is distinguishable from dashboards/alerts.
- [ ] Every production alert has an owner and actionable runbook.
- [ ] Dashboard/alert definitions are version-controlled and deployed through CI.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Testing & Certification

## INV-70-C083 — Integration certification across all supported layers and tiers

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `tests/test_integration.py`  
> Tests/evidence: `tests/test_integration.py`  
> Remaining: dev / prod / edge tiers certified in-process; real multi-layer environment not available.

**Priority:** P0  
**Canonical requirement:** Create integration tests with every supported adjacent layer and execution tier.  
**Current v4.2.0 gap:** No tests with every supported adjacent architectural layer/execution tier.

**Target artifacts**
- [ ] `tests/certification/integration-matrix.yaml`
- [ ] `tests/certification/integration/`
- [ ] `evidence/integration-certification/`

### Engineering implementation checklist

- [ ] Enumerate every supported adjacent architectural layer and execution tier from contract/ADR/deployment profiles, not only the four currently named dependencies.
- [ ] Create a machine-readable Cartesian compatibility/test matrix filtered to valid supported combinations.
- [ ] Define a common contract-test harness for authentication, run submission, capability mediation, cancellation, result/trap mapping, telemetry correlation, and release lineage.
- [ ] Run each valid adjacent-layer/tier combination in an isolated reproducible environment.
- [ ] Include positive, boundary, failure, timeout, cancellation, overload, degraded-mode, and version-mismatch cases.
- [ ] Include tenant-isolation tests across tier boundaries and remote/local dependency variants.
- [ ] Include Wasm runtime and worker/process boundary behavior in production-like deployment topology.
- [ ] Record exact versions/digests/config generations and environment profile with every test result.
- [ ] Mark unsupported combinations explicitly rather than allowing implicit skips.
- [ ] Generate certification evidence that maps each combination to PASS/FAIL/WAIVED with expiry.

### Verification and adversarial test checklist

- [ ] Compare the matrix against declared supported layers/tiers and fail on any untested supported combination.
- [ ] Remove one required environment/dependency in a negative CI job and verify certification fails rather than skips.
- [ ] Run a rolling mixed-version scenario across representative adjacent layers.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every supported adjacent layer and execution tier has executable interoperability evidence.
- [ ] No required combination can be silently skipped.
- [ ] Integration certification is a blocking input to RELEASE_EVIDENCE.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C084 — Cross-platform/runtime/provider/protocol compatibility matrix

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `docs/COMPATIBILITY.md`, `.github/workflows/ci.yml`  
> Tests/evidence: `tests/test_semantics.py::Versions`  
> Remaining: Matrix defined; only CPython 3.11 / Linux x86_64 was actually exercised.

**Priority:** P1  
**Canonical requirement:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Fast agent sandbox.  
**Current v4.2.0 gap:** No compatibility matrix/test execution across CPU architectures, Python runtimes, Wasm runtimes, hypervisors, providers, or protocol versions.

**Target artifacts**
- [ ] `COMPATIBILITY.yaml`
- [ ] `tests/compatibility/`
- [ ] `evidence/compatibility/`

### Engineering implementation checklist

- [ ] Declare supported CPU architectures explicitly (for example x86_64/ARM64 only if actually certified) rather than implying portability.
- [ ] Declare supported OS/runtime environments and exact Python ranges for control/embedding code.
- [ ] Declare approved Wasm runtime versions/builds and feature sets.
- [ ] Declare hypervisor/container/provider environments only where relevant to supported deployment tiers; mark non-applicable entries explicitly.
- [ ] Declare supported PK_FASTBOX protocol, WIT/ABI, configuration-schema, evidence-schema, and adjacent-layer versions.
- [ ] Define mandatory versus optional feature flags for each combination.
- [ ] Automate compatibility jobs across the matrix using pinned environments or trusted runners.
- [ ] Run core semantic conformance vectors on every architecture/runtime combination to detect endianness, integer, float, Unicode, timing, or interruption differences.
- [ ] Run security boundary tests and resource-limit tests on every production-supported runtime/architecture, not just functional smoke tests.
- [ ] Capture unavailable combinations as UNSUPPORTED rather than PASS/SKIP.

### Verification and adversarial test checklist

- [ ] Ensure CI compares declared support to executed jobs and fails on coverage gaps.
- [ ] Run protocol N/N-1 mixed-version tests where support is claimed.
- [ ] Compare deterministic guest test vectors across architectures/runtimes and investigate any divergence.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Compatibility claims are exactly backed by passing matrix entries.
- [ ] Unsupported platforms are rejected/documented instead of silently operating untested.
- [ ] Matrix/version data is consumed by release admission and artifact policy.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C085 — Fuzzing and property-based testing of untrusted inputs/boundaries

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `tests/test_fuzz.py`  
> Tests/evidence: `tests/test_fuzz.py`  

**Priority:** P0  
**Canonical requirement:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Fast agent sandbox.  
**Current v4.2.0 gap:** No fuzz harness/corpus/property-based campaign for bytecode/schema/untrusted input.

**Target artifacts**
- [ ] `tests/fuzz/`
- [ ] `tests/property/`
- [ ] `fuzz/corpus/`
- [ ] `docs/FUZZING.md`

### Engineering implementation checklist

- [ ] Build a property-based generator for Python-VM bytecode/instructions until the Wasm path replaces or supplements it, including malformed container types, arity, jump targets, values, limits, and capabilities.
- [ ] Fuzz Wasm module/component validation with malformed/truncated/oversized binaries and adversarial section structures using the selected runtime’s safe parsing API.
- [ ] Fuzz WIT/RPC/run/result/host-call schema decoders with invalid types, unknown fields, huge lengths, duplicate fields, boundary integers, invalid UTF-8 where applicable, and nesting bombs.
- [ ] Fuzz configuration and policy parsers plus merge/provenance envelopes.
- [ ] Fuzz capability names and diagnostic/log fields for injection/control characters/cardinality abuse.
- [ ] Fuzz host-call returned values and error paths, including oversized values and unsupported types.
- [ ] Define invariants: no Python object escape, no uncaught crash, bounded memory/time, deterministic validation result, no unauthorized host call, and no secret disclosure.
- [ ] Seed corpus with every historical bug/regression and boundary case from unit tests.
- [ ] Persist minimized crashing inputs and automatically convert fixed crashes into regression tests.
- [ ] Run short deterministic fuzz/property jobs in presubmit and longer campaigns on scheduled/release infrastructure.
- [ ] For native Wasm runtime components, use upstream/runtime-supported fuzz/sanitizer evidence where available and maintain local integration boundary fuzzing.

### Verification and adversarial test checklist

- [ ] Prove fuzz harnesses themselves enforce per-case time/memory limits so a hang does not stall the campaign.
- [ ] Run campaigns under normal and optimized Python modes for the reference path.
- [ ] Fail certification on reproducible crash, unauthorized call, resource-bound bypass, or secret leak.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every untrusted parser/boundary has an active fuzz or property-based strategy.
- [ ] Corpus and minimized regressions are version-controlled.
- [ ] Fuzz campaign results are machine-readable release evidence.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C088 — Benchmark, soak, burst, and fleet-scale certification

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `tools/bench.py`  
> Tests/evidence: `perf/baseline.json`  
> Remaining: Benchmark and burst done locally; soak and fleet-scale not run.

**Priority:** P1  
**Canonical requirement:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Fast agent sandbox.  
**Current v4.2.0 gap:** No benchmark, soak, burst, or fleet-scale certification tests.

**Target artifacts**
- [ ] `tests/certification/performance/`
- [ ] `evidence/soak/`
- [ ] `evidence/fleet-scale/`

### Engineering implementation checklist

- [ ] Define certification workloads and load generators separate from microbenchmarks.
- [ ] Create long-duration soak tests with approved minimum duration to detect memory leaks, handle leaks, queue growth, cache drift, timer drift, and telemetry degradation.
- [ ] Create burst tests with abrupt concurrency/load spikes and validate admission/load-shed behavior plus recovery.
- [ ] Create sustained overload tests to verify bounded queues/memory and circuit/retry stability.
- [ ] Create fleet-scale tests using enough workers/nodes or faithful simulation to validate routing, configuration rollout, observability cardinality, and aggregate control-plane behavior.
- [ ] Create mixed-tenant/workload tests with skewed distributions to measure fairness and noisy-neighbor isolation.
- [ ] Include rolling upgrade/config activation during load.
- [ ] Include dependency degradation/failure during soak and measure recovery without restarting the whole fleet unless required.
- [ ] Collect latency/throughput/error/saturation/resource plus process-count/FD/thread/task/cache metrics and compare start versus end.
- [ ] Record exact scale parameters, seeds, versions/digests, environment, and raw results.

### Verification and adversarial test checklist

- [ ] Assert resource slopes over soak remain within approved bounds rather than checking only final absolute values.
- [ ] Repeat burst/fleet scenarios to distinguish deterministic regressions from test noise.
- [ ] Validate all accepted requests receive one terminal outcome during scale events.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Soak, burst, and fleet-scale tests have approved pass criteria and current passing evidence.
- [ ] No unbounded resource growth or control-plane collapse is observed.
- [ ] Certification artifacts feed the release gate.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C089 — Disaster, partition, reconnect, and degraded-control-plane tests

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `tests/test_integration.py::Faults`  
> Tests/evidence: `tests/test_integration.py::Faults`  
> Remaining: Trust/time/audit outage, control-plane partition, drain and reconnect simulated in-process; no real network partition test.

**Priority:** P1  
**Canonical requirement:** Create disaster, partition, reconnect, and degraded-control-plane tests.  
**Current v4.2.0 gap:** No disaster/partition/reconnect/degraded-control-plane test suite for embedding/deployment.

**Target artifacts**
- [ ] `tests/disaster/`
- [ ] `docs/DISASTER_TEST_PLAN.md`
- [ ] `evidence/disaster/`

### Engineering implementation checklist

- [ ] Define disaster scenarios at process, node, site, dependency, and control-plane scope consistent with supported deployment profiles.
- [ ] Test hard network partition between worker and control plane while local execution is idle and while a run is active.
- [ ] Test partition between INV-70 and capability provider, policy/identity service, observability backend, and artifact source.
- [ ] Test reconnect with queued/cached configuration, policy, trust material, and telemetry to detect stale replay or update storms.
- [ ] Test control-plane restart and stale controller messages using generation/fencing protections.
- [ ] Test site/node replacement and failover eligibility under residency/attestation/config-generation constraints.
- [ ] Test expired cached trust/policy material during prolonged disconnect and require transition to the documented safe state.
- [ ] Test buffered telemetry/audit flush ordering/integrity after reconnect.
- [ ] Test rolling upgrade interrupted by partition and subsequent reconciliation.
- [ ] Measure recovery time, duplicate/lost operations, stale-config window, audit continuity, and resource cleanup.

### Verification and adversarial test checklist

- [ ] Run each scenario with deterministic network/fault controls and preserve timeline artifacts.
- [ ] Assert no operation executes under an unauthorized stale policy/config generation after reconnect.
- [ ] Assert no cross-tenant data or duplicate side effect arises during partition/retry/failover.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Disaster/partition behavior matches documented failover/degraded-mode/precedence policy.
- [ ] Reconnect does not create stale-control or duplicate-execution hazards.
- [ ] Current passing disaster evidence is required for production certification.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C090 — Machine-readable production release acceptance evidence

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `tools/release_evidence.py`, `RELEASE_EVIDENCE.json`  
> Tests/evidence: `tests/test_governance.py::Evidence`  

**Priority:** P0  
**Canonical requirement:** Require machine-readable acceptance evidence before certifying a Fast agent sandbox release for production.  
**Current v4.2.0 gap:** No machine-readable release acceptance evidence is shipped; CHECKLIST.json is a requirement list, not acceptance proof.

**Target artifacts**
- [ ] `schemas/release-evidence.schema.json`
- [ ] `RELEASE_EVIDENCE.json`
- [ ] `tools/verify_release_evidence.py`

### Engineering implementation checklist

- [ ] Define a versioned release-evidence schema keyed by INV-70 release version and immutable package/artifact digest.
- [ ] Include source commit, build/provenance digest, dependency lock digest, SBOM digest, selected Wasm runtime/version/digest, and configuration/compatibility schema versions.
- [ ] Include RTM digest and counts by verification state; a requirement list alone must not count as evidence.
- [ ] Include unit, optimized-mode, integration, compatibility, fuzz, fault-injection, disaster, performance, soak/fleet, and security test result references with pass/fail status.
- [ ] Include performance-gate result and baseline/profile identifiers.
- [ ] Include artifact signature/provenance verification results and vulnerability/dependency scan summary according to policy.
- [ ] Include open exceptions/waivers with owners/expiry and fail if an expired or unapproved waiver is referenced.
- [ ] Include required architecture/security/operations/release approvals as signed/identity-bound attestations where supported.
- [ ] Include generated timestamp plus evidence schema version, but identify evidence primarily by digest so timestamp is not the trust anchor.
- [ ] Sign/integrity-protect the final evidence bundle and store it immutably with the release.
- [ ] Build a verifier that resolves referenced evidence, validates digests/schema/signatures, and recomputes gating logic.

### Verification and adversarial test checklist

- [ ] Remove or alter each mandatory evidence class in negative fixtures and prove certification fails.
- [ ] Tamper with a referenced report and verify digest/signature failure.
- [ ] Attempt to certify with skipped/unexecuted required tests and verify FAIL, not PASS.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Production certification is impossible without a valid complete RELEASE_EVIDENCE.json bundle.
- [ ] All evidence is machine-verifiable and content-addressed.
- [ ] The release artifact and evidence bundle mutually identify the same source/build/version.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Operations, Release & Governance

## INV-70-C093 — Supported-version compatibility matrix and enforcement

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `semantics.py::SUPPORTED_PEER_RELEASES/check_peer_release`, `docs/COMPATIBILITY.md`  
> Tests/evidence: `tests/test_semantics.py::Versions.test_peer_window`  

**Priority:** P1  
**Canonical requirement:** Maintain a supported-version compatibility matrix for Fast agent sandbox and adjacent dependencies.  
**Current v4.2.0 gap:** No supported-version compatibility matrix for Python/pk_core/Wasm/adjacent components.

**Target artifacts**
- [ ] `COMPATIBILITY.yaml`
- [ ] `docs/SUPPORTED_VERSIONS.md`
- [ ] `tools/check_compatibility.py`

### Engineering implementation checklist

- [ ] Define support rows for INV-70 package version, Python version, pk_core version, Wasm runtime version, WIT/ABI version, protocol versions, adjacent INV-69/INV-09/INV-71/GAP-09 versions, OS, and architecture as applicable.
- [ ] Distinguish TESTED, SUPPORTED, DEPRECATED, END_OF_LIFE, UNSUPPORTED, and BLOCKED/VULNERABLE states.
- [ ] Record first-supported and last-supported release where known, plus planned EOL date for deprecated combinations.
- [ ] Identify minimum required security features/runtime flags for each Wasm runtime version.
- [ ] Define mixed-version rolling-upgrade windows and compatibility constraints.
- [ ] Generate runtime/build startup checks that reject known-unsupported combinations in production rather than merely warning.
- [ ] Link every SUPPORTED combination to current automated compatibility evidence.
- [ ] Update the matrix through code review when dependencies change; prohibit undocumented support expansion.
- [ ] Expose current dependency/runtime versions in diagnostics/release evidence for matrix evaluation.
- [ ] Define how emergency vulnerable-version blocks override normal support windows.

### Verification and adversarial test checklist

- [ ] CI-compare the matrix against actual compatibility jobs and fail if a SUPPORTED row lacks evidence.
- [ ] Test startup/admission under blocked/unsupported runtime versions.
- [ ] Test a rolling upgrade using the supported mixed-version window.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Operators can determine exactly which version combinations are supported.
- [ ] Production prevents known-unsupported/blocked combinations.
- [ ] Support claims are evidence-backed and release-versioned.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C094 — Patching, vulnerability response, and end-of-life policy

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `ops/VULNERABILITY_AND_EOL.md`  
> Tests/evidence: `tests/test_governance.py::Docs`  
> Remaining: Policy written; owner adoption and a scanner feed are pending.

**Priority:** P0  
**Canonical requirement:** Define patching, vulnerability response, and end-of-life SLAs for Fast agent sandbox.  
**Current v4.2.0 gap:** No patching, vulnerability response, security advisory, or end-of-life SLA/policy.

**Target artifacts**
- [ ] `SECURITY.md update`
- [ ] `docs/VULNERABILITY_RESPONSE.md`
- [ ] `docs/SUPPORT_POLICY.md`

### Engineering implementation checklist

- [ ] Define vulnerability intake channels, private reporting path, triage owner, and acknowledgement workflow.
- [ ] Define severity model and approved remediation/mitigation SLAs for runtime escapes, capability/auth bypass, dependency CVEs, denial of service, information disclosure, and lower-severity defects.
- [ ] Define emergency response for a Wasm runtime or native dependency vulnerability: version block, capability disable, traffic drain, rollback, or patched rebuild.
- [ ] Define continuous/scheduled dependency and vulnerability scanning for Python, native Wasm runtime artifacts, images/packages, and build tooling.
- [ ] Define affected-version analysis and how supported releases receive patches.
- [ ] Define security advisory content, disclosure coordination, CVE handling where applicable, and customer/operator notification.
- [ ] Define cryptographic signing/provenance requirements for security patches and prohibit unsigned emergency binaries.
- [ ] Define supported release branches, maintenance window, deprecation notice, and end-of-life dates/policy.
- [ ] Define what happens at EOL: no new deployment certification, upgrade requirement, and artifact/support status.
- [ ] Define post-remediation regression/fuzz/security testing and evidence required before closing a vulnerability.

### Verification and adversarial test checklist

- [ ] Run a tabletop critical runtime-CVE exercise from detection through block/patch/release/notification.
- [ ] Test that compatibility/artifact policy can block a vulnerable runtime version quickly.
- [ ] Verify an EOL/blocked version cannot satisfy release certification without an explicit non-production override.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Patch/vulnerability/EOL responsibilities and time objectives are explicit and owned.
- [ ] Emergency security changes retain signature/provenance/evidence controls.
- [ ] Version support status is synchronized with COMPATIBILITY.yaml.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C097 — Incident severity, paging, containment, and recovery procedures

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `RUNBOOK.md`  
> Tests/evidence: `tests/test_governance.py::Docs`  
> Remaining: Severity, containment and recovery defined; paging target is UNASSIGNED.

**Priority:** P0  
**Canonical requirement:** Define incident severity, paging, escalation, containment, and recovery procedures.  
**Current v4.2.0 gap:** No incident severity/paging/escalation/containment/recovery procedure.

**Target artifacts**
- [ ] `docs/INCIDENT_RESPONSE.md`
- [ ] `docs/runbooks/incident-*.md`
- [ ] `config/incident-routing.yaml`

### Engineering implementation checklist

- [ ] Define incident severity levels using impact/scope/security criteria and map each level to paging/escalation expectations.
- [ ] Define detection sources: SLO alerts, security audit anomalies, artifact verification failure, sandbox escape indicators, overload, dependency outage, and performance regression.
- [ ] Define primary/secondary paging routes from the ownership model and an incident commander/security lead assignment process.
- [ ] Define containment actions that preserve evidence: disable/revoke a capability, block an artifact/runtime version, drain a node/site, fail closed admissions, rotate trust material, or roll back configuration/release.
- [ ] Define which containment actions are safe to automate versus require human approval.
- [ ] Define forensic evidence to preserve: audit chain, logs/traces, release/config/artifact digests, process/runtime version, failure inputs if safe, and timeline.
- [ ] Define tenant/isolation breach handling separately from ordinary availability incidents.
- [ ] Define recovery validation before reopening traffic: clean runtime, verified artifacts, configuration/trust state, health, smoke/integration tests, and monitoring stability.
- [ ] Define communication and status update responsibilities without exposing tenant secrets.
- [ ] Define post-incident review, corrective-action ownership, due dates, and linkage to exceptions/technical debt.

### Verification and adversarial test checklist

- [ ] Run tabletop exercises for sandbox escape suspicion, capability-provider compromise, widespread timeout/overload, and bad configuration rollout.
- [ ] Run at least one technical game-day executing containment/rollback procedures in a safe environment.
- [ ] Verify paging/runbook links and access permissions before incidents.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Every critical incident class has a severity, owner, paging route, containment action, and recovery gate.
- [ ] Containment can be executed without inventing unsafe steps during an incident.
- [ ] Exercises produce tracked follow-up evidence.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C098 — Recurring access, policy, dependency, configuration, and architecture reviews

> **4.3.0 remediation status: PARTIAL**  
> Implementation: `ops/REVIEWS.md`  
> Tests/evidence: `tests/test_governance.py::Docs`  
> Remaining: Review schedule defined; no review has been held yet.

**Priority:** P2  
**Canonical requirement:** Perform recurring access, policy, dependency, configuration, and architecture reviews.  
**Current v4.2.0 gap:** No recurring access/policy/dependency/configuration/architecture review cadence or owner.

**Target artifacts**
- [ ] `governance/REVIEW_SCHEDULE.yaml`
- [ ] `governance/reviews/`
- [ ] `tools/check_review_freshness.py`

### Engineering implementation checklist

- [ ] Define recurring review types for privileged access/roles, capability policy, trust roots/issuers, dependencies/runtime versions, vulnerability posture, configuration defaults/overlays, telemetry/privacy policy, and architecture/ADR assumptions.
- [ ] Assign an accountable owner and required reviewers for each review type.
- [ ] Define cadence and maximum staleness appropriate to risk; record next_due and last_completed in machine-readable form.
- [ ] Define required review inputs: changes since last review, incident findings, exceptions/waivers, dependency advisories, compatibility status, and audit/telemetry findings.
- [ ] Define review outputs: approved/no-change, remediation actions, revoked access/policy, ADR update, dependency upgrade, or new waiver with expiry.
- [ ] Keep signed/identity-attributed review records with scope, date, participants, evidence reviewed, findings, and actions.
- [ ] Automatically flag overdue reviews in CI/release governance where they affect production certification.
- [ ] Link review findings to tracked issues/work packages and verify closure at subsequent review.
- [ ] Include periodic least-privilege review of capability grants and control-plane roles.
- [ ] Include architecture review whenever the sandbox/runtime/trust boundary changes materially, regardless of calendar cadence.

### Verification and adversarial test checklist

- [ ] Create a synthetic overdue review and verify the freshness checker/reporting flags or blocks according to policy.
- [ ] Check every required review has an active owner and next_due date.
- [ ] Sample closed findings and verify linked remediation evidence exists.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] Governance reviews occur on a defined owned cadence and cannot silently expire.
- [ ] Findings create traceable remediation work.
- [ ] Architecture/security assumptions are periodically revalidated against the deployed system.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

## INV-70-C099 — Exception, waiver, technical-debt, and deprecation register

> **4.3.0 remediation status: VERIFIED**  
> Implementation: `EXCEPTIONS.yaml`  
> Tests/evidence: `tests/test_governance.py::Exceptions`  

**Priority:** P1  
**Canonical requirement:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.  
**Current v4.2.0 gap:** No exception/waiver/technical-debt/deprecation register with owners and expiry dates.

**Target artifacts**
- [ ] `governance/EXCEPTIONS.yaml`
- [ ] `governance/DEBT.yaml`
- [ ] `governance/DEPRECATIONS.yaml`
- [ ] `tools/check_governance_registers.py`

### Engineering implementation checklist

- [ ] Define a unique ID and schema for each exception/waiver containing requirement/control, affected scope/version, rationale, risk, compensating controls, owner, approver, created_at, expiry, and renewal count.
- [ ] Distinguish temporary risk acceptance from permanent design decision; permanent changes require requirement/ADR updates rather than never-expiring waivers.
- [ ] Link every waiver to exact RTM requirement IDs and release evidence.
- [ ] Block expired, unapproved, ownerless, or scope-mismatched waivers in release certification.
- [ ] Define a technical-debt register with severity/impact, component, owner, target release/date, dependencies, and remediation acceptance criteria.
- [ ] Define a deprecation register for protocol/ABI/config/runtime behaviors with announced release, replacement, last-supported release/date, telemetry for remaining usage, and removal criteria.
- [ ] Require compensating controls and monitoring for security/reliability waivers.
- [ ] Define renewal process requiring fresh risk review; never auto-renew by date manipulation alone.
- [ ] Expose open waiver/debt/deprecation counts in governance/release reporting without treating debt presence itself as proof of failure.
- [ ] Close entries only with concrete implementation/test/evidence links.

### Verification and adversarial test checklist

- [ ] Test expired/ownerless/unapproved waiver fixtures and ensure release verification fails.
- [ ] Test a waiver tied to the wrong version/scope and ensure it cannot apply.
- [ ] Check every deprecated behavior has a replacement/removal plan and usage signal where measurable.
- [ ] Add deterministic automated tests for all newly introduced reason/status codes and boundary conditions.
- [ ] Run the relevant tests in a clean environment with pinned dependencies; a missing dependency or skipped required test must not be reported as PASS.
- [ ] Add regression coverage for any defect found while implementing this work package.

### Evidence, documentation, and release-gate checklist

- [ ] Update the relevant architecture/runtime/security/operations documentation and cross-link this requirement ID.
- [ ] Add or update the `requirements/RTM.yaml` row for this check ID with implementation symbols, tests, evidence references, owner, and verification status.
- [ ] Produce machine-readable evidence carrying the INV-70 release version, source revision, dependency/runtime versions, configuration digest, and result.
- [ ] Ensure evidence is referenced by `RELEASE_EVIDENCE.json` once C090 is implemented.
- [ ] Add ownership and review expectations; security- or reliability-sensitive changes require the corresponding specialist approval.
- [ ] Do not change status to VERIFIED until the implementation, automated tests, and required evidence all exist.

### Definition of done / acceptance gate

- [ ] All production exceptions and known debt are explicit, owned, scoped, and time-bounded where appropriate.
- [ ] Expired waivers cannot silently certify a release.
- [ ] Closure and deprecation removal are evidence-backed.
- [ ] The requirement has no unresolved contradiction with `contract.py`, `RUNTIME_SPEC.md`, `SECURITY.md`, the approved ADRs, or deployment profiles.
- [ ] CI/release certification fails when the component or its required evidence is removed, invalid, expired, skipped, or tampered with.
- [ ] The post-remediation audit marks this requirement `VERIFIED` (or another explicitly approved non-missing state) with direct evidence links.

---

# Final production-readiness closure checklist

- [ ] Re-run the dependency-free runtime/security tests under normal and optimized Python modes.
- [ ] Run the pinned `pk_core` conformance suite; required conformance must not be skipped.
- [ ] Run the selected Wasm runtime conformance/security suite and malicious-module tests.
- [ ] Run all adjacent-layer integration and compatibility matrices.
- [ ] Run fuzz/property, fault-injection, disaster/partition, performance, soak/burst/fleet, and regression suites.
- [ ] Generate fresh SBOM, provenance, artifact signatures/digests, compatibility matrix, RTM, audit matrix, and release evidence.
- [ ] Verify no expired waiver, unsupported runtime/dependency, overdue mandatory review, or unresolved P0 requirement is present.
- [ ] Independently verify the security audit chain and release-evidence bundle.
- [ ] Perform a second-pass 100-item audit against the updated repository; preserve the old v4.2.0 audit as historical evidence rather than overwriting it.
- [ ] Version-bump only after implementation/testing/evidence are internally consistent and the final release gate passes.

## Coverage assertion

This document contains remediation work packages for **50 of 50** requirements marked `MISSING` in the v4.2.0 audit matrix. No missing requirement was omitted.
