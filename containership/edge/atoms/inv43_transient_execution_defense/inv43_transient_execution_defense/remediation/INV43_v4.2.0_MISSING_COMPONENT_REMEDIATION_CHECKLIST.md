# INV-43 v4.2.0 — Missing Components Remediation Checklist

**Repository:** `inv43_transient_execution_defense`  
**Baseline audited version:** 4.2.0  
**Purpose:** implementation-grade remediation plan for all 52 components/evidence gaps identified by the post-hardening audit.  
**Status convention:** unchecked boxes are required unless the component is formally marked not-applicable by an approved architecture/governance decision.  

> This checklist is intentionally stricter than a feature to-do list. A component is complete only when implementation, negative/failure testing, machine-readable evidence, operational ownership, and release-gate behavior are all demonstrated.

## Global engineering rules for every checklist item

- [ ] Use fail-closed behavior for security-critical uncertainty: unknown, stale, unauthenticated, unsupported, or contradictory posture must never silently become a cross-tenant permit.
- [ ] Preserve the separation between observed node facts and policy-derived conclusions. Never report a mitigation active solely from CPU generation, documentation, or configuration intent.
- [ ] Version every externally visible contract and configuration/policy/evidence format; document breaking-change and compatibility behavior.
- [ ] Do not rely on Python `assert` for runtime security checks; verification must continue to pass meaningfully under `python -O`.
- [ ] All release evidence must bind to the exact INV-43 artifact/source digest, dependency versions, configuration/policy versions, and test environment.
- [ ] Every BLOCKER/HIGH item remains production-gating until implemented and evidenced or covered by a formally approved, time-bounded risk acceptance.
- [ ] Any new remote boundary must include authentication, authorization, timeout/cancellation, idempotency, bounded retry, backpressure, size/concurrency limits, structured errors, and adversarial tests.
- [ ] Any new durable or transmitted sensitive data makes encryption/key-management applicability explicit; do not assume C047 is satisfied by the current in-process design once architecture changes.
- [ ] Any secret/credential-bearing integration must keep secret material out of ordinary config/logs/metrics/evidence and add dedicated leakage tests.
- [ ] Update the requirements traceability matrix and `AUDIT_REPORT.md` whenever a gap changes state; do not delete historical evidence of previously open findings.

## Recommended implementation order

1. **Release/provenance foundation:** 1-8, 23, 50-52.
2. **Authoritative security signal path:** 9-14, 16-18, 24-27.
3. **Placement enforcement and service boundaries:** 15, 19-22, 28-33.
4. **Performance/observability/certification:** 34-44.
5. **Operations and lifecycle:** 45-49.

---

## 01. Original `MASTER.md` / master-prompt provenance artifact

**Severity:** BLOCKER  
**Related controls:** C020, C045, C090, C100  
**Audit basis:** The 4.1.0 README claimed it existed, but it was not in the archive. 4.2.0 does not fabricate it.  
**Objective:** Restore authoritative provenance for the component without fabricating history, and make the source-to-requirement lineage independently auditable.

### Required deliverables

- [ ] The original `MASTER.md`, recovered from the authoritative source if it exists.
- [ ] A provenance record containing source URI/path, immutable digest, author/owner, retrieval date, and approval status.
- [ ] A documented fallback decision if the original artifact cannot be recovered.

### Architecture and implementation checklist

- [ ] Search approved source repositories, release bundles, artifact stores, and change records for the exact master artifact referenced by 4.1.0.
- [ ] Verify candidate provenance using repository history, signed commits/tags, release manifests, or independent owner confirmation; do not infer provenance from filename alone.
- [ ] Compute SHA-256 (and organization-standard stronger/signing metadata if applicable) for the recovered artifact and record it in a machine-readable provenance manifest.
- [ ] Map every requirement derived from the master artifact to a stable source anchor/section ID and to the corresponding checklist/control IDs.
- [ ] If the artifact is permanently unavailable, open a formal provenance exception that states the loss, impact, compensating evidence, owner, review date, and expiry/remediation plan.
- [ ] Update README/AUDIT_REPORT references so presence/absence is mechanically checkable and no documentation claims an artifact that is not packaged.
- [ ] Ensure the artifact is immutable in release packages; changes require a new digest, review, and release note.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Add a verifier that fails when a declared provenance artifact is absent or its digest differs.
- [ ] Test both recovered-artifact and approved-exception paths.
- [ ] Retain the provenance manifest and verifier result under `evidence/provenance/`.
- [ ] Review traceability from source paragraphs to C020/C045/C090/C100 evidence.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Production certification must remain closed until the source artifact is recovered or a formally approved exception replaces it.
- [ ] No release may claim original master-prompt provenance without artifact-backed evidence.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 02. `pk_core` runtime source/package plus an approved version pin

**Severity:** BLOCKER  
**Related controls:** C016, C027, C031, C093, C100  
**Audit basis:** Registry contract/gate behavior cannot be executed or certified from this archive alone.  
**Objective:** Make the external registry/runtime dependency reproducible, version-bounded, testable, and enforceable during release certification.

### Required deliverables

- [ ] Pinned `pk_core` package/source coordinate and approved version range.
- [ ] Dependency lock entry with cryptographic hashes.
- [ ] Compatibility contract and release-gate integration.

### Architecture and implementation checklist

- [ ] Identify the authoritative `pk_core` distribution channel and exact package/module identity consumed by `component.py` and `contract.py`.
- [ ] Pin a minimum/maximum compatible version or exact release according to platform policy; document why the range is safe.
- [ ] Record transitive dependencies and hashes in the lock mechanism selected for the repository.
- [ ] Declare the required `pk_core.contract.Contract`, `Dependency`, `Slo`, registry-list/run/gate/verify CLI semantics as explicit compatibility assumptions.
- [ ] Fail startup/conformance with a stable error when an unsupported `pk_core` version is present; do not silently downgrade capability.
- [ ] Make `PK_REQUIRE_CORE=1` mandatory in release CI and production certification jobs.
- [ ] Vendor or cache approved artifacts only if organizational supply-chain policy permits; otherwise document deterministic retrieval.
- [ ] Expose the resolved `pk_core` version in verification evidence and runtime version/health output.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Run adapter unit tests against the minimum and maximum supported `pk_core` versions.
- [ ] Run `python -m pk_core list`, `run INV-43`, `gate INV-43`, and `verify` in clean environments.
- [ ] Add a negative test for missing and unsupported versions.
- [ ] Capture lockfile, package digest, command output, and gate result as release evidence.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A release is not certifiable if `pk_core` is absent, unpinned, outside the approved range, or the external gate cannot execute.
- [ ] All adapter tests and the sealed external gate must pass from a clean environment using only declared dependencies.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 03. Machine-readable conformance/evidence outputs (`evidence/`, `conformance/`, sealed gate result)

**Severity:** BLOCKER  
**Related controls:** C020, C090, C100  
**Audit basis:** README shows external commands, but no resulting evidence ledger or gate artifact is supplied.  
**Objective:** Produce durable, machine-readable certification evidence for every release instead of relying on console output or documentation examples.

### Required deliverables

- [ ] `evidence/pk_evidence.jsonl` or equivalent append-only evidence ledger.
- [ ] `conformance/PK_GATE_RESULTS.json` with schema/version, release identity, timestamps, and control results.
- [ ] A sealed/signature or digest record binding evidence to the exact source/artifact under test.

### Architecture and implementation checklist

- [ ] Define a versioned evidence schema with release version, commit/artifact digest, environment fingerprint, tool versions, control IDs, result, reason, and evidence references.
- [ ] Run the standalone verifier and external `pk_core` gate in the same release workflow; reject partial evidence sets.
- [ ] Bind each evidence record to `INV-43`, version 4.2.x+, and immutable artifact digest rather than a mutable workspace path.
- [ ] Make evidence generation deterministic and non-interactive; prohibit manual editing after generation.
- [ ] Add a sealing step using approved signing/attestation infrastructure or, at minimum, a manifest digest chained to build provenance.
- [ ] Store evidence with retention sufficient for incident response, audit, and rollback lineage.
- [ ] Redact secrets/high-cardinality tenant data before persistence while preserving stable identifiers needed for correlation.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Schema-validate all evidence files in CI.
- [ ] Verify tamper detection by altering a record and confirming verification fails.
- [ ] Ensure missing, stale, or mismatched release digests fail the production gate.
- [ ] Cross-check evidence completeness against the requirements traceability matrix.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Production exit gate consumes machine-readable evidence only; screenshots or console text are supplemental, not authoritative.
- [ ] Evidence must uniquely identify the released artifact and be independently verifiable after the build environment is gone.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 04. Reproducible package/build metadata (`pyproject.toml` or equivalent), dependency lock, and supported Python declaration

**Severity:** HIGH  
**Related controls:** C016, C031, C032, C040, C045  
**Audit basis:** The package is source-only; installation and dependency resolution are not reproducibly specified.  
**Objective:** Make installation, dependency resolution, supported runtimes, builds, and verification reproducible from an empty environment.

### Required deliverables

- [ ] `pyproject.toml` (or approved equivalent) with package metadata and build backend.
- [ ] A locked dependency set with hashes and platform markers.
- [ ] Declared supported Python versions and reproducible build instructions.

### Architecture and implementation checklist

- [ ] Define package name, version source, modules/packages, Python requirement, classifiers, license metadata placeholder, and build backend.
- [ ] Separate runtime, optional `pk_core`, test, schema-validation, benchmark, fuzz, and development dependency groups.
- [ ] Choose and document a lock workflow; commit the lock or constraints file according to policy.
- [ ] Pin `jsonschema` for conformance jobs rather than relying on ambient installation.
- [ ] Ensure version 4.2.x is single-sourced so `VERSION`, package metadata, and module reporting cannot drift.
- [ ] Create source distribution/wheel build jobs and verify reproducibility or document allowed nondeterministic fields.
- [ ] Document Windows invocation using `py -3`/`python`, path constraints, and clean virtual-environment bootstrap.
- [ ] Define support policy for Python minor versions and dates for adding/removing versions.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Build and install into clean Windows and Linux virtual environments.
- [ ] Run `verify.py`, `python -O verify.py`, schema validation, and package import from installed wheel rather than source tree.
- [ ] Run dependency-resolution checks with no undeclared packages available.
- [ ] Generate and compare artifact hashes across repeated builds where reproducible-build policy applies.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A clean machine can build, install, verify, and uninstall INV-43 using only committed metadata plus approved package sources.
- [ ] Release CI rejects version drift, unlocked dependencies, unsupported Python, or undeclared imports.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 05. Approved architecture decision record for transient-execution defense

**Severity:** HIGH  
**Related controls:** C010  
**Audit basis:** No approved ADR is present.  
**Objective:** Create an approved architecture decision record that defines the transient-execution defense boundary, trust model, technology choices, and non-goals.

### Required deliverables

- [ ] An ADR with status, date, decision owners/approvers, alternatives, consequences, and supersession rules.
- [ ] Architecture diagrams showing trust boundaries and adjacent components.
- [ ] Explicit decisions for SFI applicability, read-back authority, policy ownership, and service-vs-library deployment.

### Architecture and implementation checklist

- [ ] Document the problem statement: cross-instance hardware side-channel risk, mitigation-state honesty, SMT/core-scheduling policy, and measurable overhead.
- [ ] Define the authoritative source of truth as node read-back and state why CPU model assumptions alone are insufficient.
- [ ] Record the baseline mitigation set (`spectre_v2`, `l1tf`, `mds`, `mmio_stale_data`) and the mechanism for evolving it.
- [ ] Decide whether INV-43 remains an in-process library or becomes a service; identify every resulting trust boundary.
- [ ] Resolve responsibility split among GAP-02, SCH-01, PLN-04, INV-34, and `pk_core`.
- [ ] Document availability and disconnected-operation assumptions for edge/site deployments.
- [ ] Record rejected alternatives, including unsafe fail-open behavior and unverified caller-supplied posture.
- [ ] Require security, platform, scheduler, and operations approval before status becomes Accepted.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Review ADR against C001-C010 and the threat model.
- [ ] Run an architecture-review checklist confirming diagrams match actual interfaces and package contents.
- [ ] Add a CI/documentation check that the accepted ADR ID is referenced by README and traceability matrix.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No production certification until the ADR is accepted by named accountable roles.
- [ ] Any incompatible boundary or trust-model change creates a new ADR or formal superseding revision.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 06. Resolution of the checklist's **Software Fault Isolation (SFI)** requirement versus the implemented mitigation-state/co-tenancy model

**Severity:** HIGH  
**Related controls:** C010, C031  
**Audit basis:** The checklist explicitly names SFI, but the repository neither implements nor pins an SFI technology/specification. SFI should not be implicitly treated as equivalent to CPU transient-execution mitigations.  
**Objective:** Resolve whether Software Fault Isolation is genuinely part of INV-43, belongs to another component, or is an erroneous inherited requirement; never treat SFI as synonymous with CPU transient-execution mitigation.

### Required deliverables

- [ ] Approved applicability decision.
- [ ] If applicable: pinned SFI specification/implementation plus integration design and tests.
- [ ] If not applicable: corrected requirement source/waiver and traceability showing the control is satisfied elsewhere or removed.

### Architecture and implementation checklist

- [ ] Define SFI precisely for this architecture: code instrumentation/sandboxing model, memory/control-flow constraints, trust assumptions, and threat classes addressed.
- [ ] Compare SFI coverage with INV-43's actual controls: hardware/kernel mitigation read-back, co-tenancy refusal, SMT/core scheduling, and workload trust classes.
- [ ] Identify whether SFI addresses any documented transient-execution cross-instance side channel in the intended deployment; cite approved internal/external technical rationale.
- [ ] If SFI is required, select the implementation/spec, pin version, define compiler/runtime verification, and specify how enforcement evidence reaches INV-43 policy decisions.
- [ ] If SFI belongs to PLN-04 or another isolation tier, define the interface and do not duplicate ownership.
- [ ] If the checklist is wrong, issue a controlled requirement correction rather than implementing unrelated technology solely to satisfy wording.
- [ ] Document residual risks that remain even with SFI and prohibit claims that SFI alone replaces microcode/kernel mitigations.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Architecture/security review signs the applicability decision.
- [ ] If implemented, add escape/bypass, malformed-module, version-compatibility, and performance tests.
- [ ] If waived/reassigned, test the traceability/gate system accepts only the approved disposition and expiry/review conditions.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] C010/C031 cannot be marked satisfied by inference; there must be an approved artifact-backed disposition.
- [ ] No release documentation may describe mitigation-state policy as SFI unless an actual SFI mechanism is present and verified.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 07. Accountable owner, escalation path, support commitment, and on-call responsibility

**Severity:** HIGH  
**Related controls:** C009, C091, C097  
**Audit basis:** No owner/team/contact/escalation artifact is supplied.  
**Objective:** Establish accountable operational ownership so security decisions, incidents, vulnerabilities, and release gates have named responsible parties and response expectations.

### Required deliverables

- [ ] `OWNERS.md` or service catalog entry.
- [ ] Primary/secondary on-call rotation and escalation matrix.
- [ ] Support/SLO commitment and contact channels.

### Architecture and implementation checklist

- [ ] Assign one accountable service owner and separate technical/security approvers where required by governance.
- [ ] Define escalation tiers for security policy rejection spikes, attestation failures, unsafe node posture, dependency outage, and release-gate failure.
- [ ] Record support hours, response targets, handoff rules, and after-hours paging expectations.
- [ ] Define who can change required mitigation policy, approve exceptions, disable placement, and rotate signing/attestation trust roots.
- [ ] Ensure least privilege for operator capabilities and require auditable change approval for high-risk actions.
- [ ] Create ownership continuity rules for staff changes and stale/unowned components.
- [ ] Link ownership to incident, vulnerability, patching, review, and exception ledgers.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Exercise the escalation tree in a tabletop drill.
- [ ] Validate every listed channel and backup contact at least quarterly.
- [ ] Make release gate fail or warn according to policy when ownership metadata is missing or stale.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Production inventory shows a current accountable owner, on-call path, and support commitment.
- [ ] No BLOCKER/HIGH waiver may be accepted without an owner and expiry.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 08. Requirements traceability matrix from all 100 requirements to concrete implementation and verification evidence

**Severity:** HIGH  
**Related controls:** C020  
**Audit basis:** `CHECKLIST.json` contains requirements only; it is not a bidirectional evidence map.  
**Objective:** Create a bidirectional requirements-to-implementation-to-test-to-evidence matrix for all 100 controls and repository-specific security claims.

### Required deliverables

- [ ] Machine-readable RTM file, e.g. `traceability/requirements.yaml`.
- [ ] Generated human-readable matrix.
- [ ] CI completeness validator.

### Architecture and implementation checklist

- [ ] Assign stable IDs C001-C100 and preserve the exact requirement text/version.
- [ ] For each control, record applicability, rationale, implementation artifact(s), test(s), evidence path(s), owner, status, and approved exception if any.
- [ ] Add reverse links from source files/tests/evidence to requirement IDs where practical.
- [ ] Separate 'implemented', 'tested', 'evidenced', and 'certified' states so one does not imply another.
- [ ] Represent conditional controls such as encryption/secrets with explicit applicability decisions.
- [ ] Track external dependencies and evidence as external references rather than marking local implementation complete.
- [ ] Generate missing-link reports and prohibit 'satisfied' status without concrete evidence.
- [ ] Version the matrix with the release and retain historical snapshots.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] CI verifies all 100 requirements appear exactly once and all referenced artifacts exist.
- [ ] Randomly sample controls and prove forward/reverse traceability during review.
- [ ] Fail certification if any applicable control lacks implementation and verification evidence or an approved waiver.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] The matrix can answer 'what proves C0xx?' and 'which requirements does this file/test prove?' without manual interpretation.
- [ ] The 52 missing components map cleanly into the RTM with status and remediation ownership.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 09. Hardware/kernel/microcode mitigation read-back collector

**Severity:** BLOCKER  
**Related controls:** C004, C021, C029, C030, C040  
**Audit basis:** `MitigationState.record()` receives caller-supplied state; it does not collect authoritative node read-back itself.  
**Objective:** Replace caller-trusted mitigation posture with authoritative hardware/OS read-back collection that measures the actual node state used for placement decisions.

### Required deliverables

- [ ] Collector module/service with platform-specific backends.
- [ ] Normalized collector output schema feeding `MitigationState`.
- [ ] Privilege model, freshness metadata, and negative/error states.

### Architecture and implementation checklist

- [ ] Define authoritative sources per supported OS/kernel/architecture: kernel vulnerability interfaces, CPU flags/MSRs where appropriate, microcode revision, SMT state, core-scheduling capability/state, hypervisor/provider signals, and vendor advisories as policy inputs—not assumptions.
- [ ] Implement parsers that distinguish `active`, `inactive`, `unknown`, `not_applicable`, and collection failure internally; normalize only after policy semantics are defined.
- [ ] Never infer 'active' from CPU family/generation alone; prefer direct read-back and verified kernel/runtime state.
- [ ] Capture raw source values or digests for forensic evidence while exposing normalized fields to `MitigationState`.
- [ ] Define privilege boundaries; use the minimum filesystem/device/kernel capabilities required by the collector.
- [ ] Make collection atomic enough that a report cannot mix materially different node states without detection.
- [ ] Integrate collector result with policy evaluation so unverified/stale/failed read-back becomes fail-closed for cross-tenant placement.
- [ ] Define update triggers for boot, microcode/kernel change, SMT/core-scheduling change, hotplug, and periodic refresh.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Golden-fixture tests for every supported kernel/read-back format and mitigation state.
- [ ] Negative tests for missing files, permission denial, malformed/truncated values, unsupported CPU/kernel, and contradictory sources.
- [ ] Hardware-in-the-loop tests on representative CPU families and virtualization environments.
- [ ] Prove caller cannot override authoritative posture through ordinary API input.
- [ ] Retain sanitized raw/normalized collector evidence with timestamps and collector version.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] BLOCKER: production cross-tenant decisions must use authenticated authoritative node observations, not arbitrary caller-provided tuples.
- [ ] Unknown or unverifiable required mitigations must continue to deny cross-tenant co-tenancy.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 10. Freshness/evidence metadata for node observations (source, timestamp/monotonic age, collector identity, stale-data TTL)

**Severity:** HIGH  
**Related controls:** C004, C014, C015, C018, C036, C057, C071  
**Audit basis:** The model stores status/cost but cannot prove when, where, or by whom the read-back was observed.  
**Objective:** Attach trustworthy observation provenance and freshness to every mitigation posture so policy cannot act on stale or unattributed state.

### Required deliverables

- [ ] Observation metadata schema.
- [ ] TTL/staleness policy per signal.
- [ ] Clock/monotonic-time handling and collector identity binding.

### Architecture and implementation checklist

- [ ] Add fields such as `observed_at`, `monotonic_age_ms`, `collector_id`, `collector_version`, `source_type`, `source_digest`, `node_boot_id`, and optional attestation reference.
- [ ] Define maximum age for security-critical posture; use shorter TTL for mutable signals such as SMT/core scheduling.
- [ ] Prefer monotonic elapsed-time checks for staleness within a boot; bind wall-clock timestamps for audit with explicit clock-quality status.
- [ ] Invalidate observations across boot ID changes, collector identity changes, kernel/microcode changes, or policy version changes when required.
- [ ] Represent stale and collection-error states distinctly in internal telemetry, while failing closed for authorization.
- [ ] Prevent a newer untrusted observation from replacing an older authenticated observation unless trust validation succeeds.
- [ ] Include freshness in `PK_MITIGATIONS/1` v2 or an extension contract with compatibility plan.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Boundary tests at TTL-1, TTL, TTL+1 and clock rollback/forward scenarios.
- [ ] Restart/reboot tests proving stale pre-boot posture is not reused.
- [ ] Schema/contract tests for metadata presence and types.
- [ ] Evidence proves decision time, observation age, collector identity, and source lineage.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A co-tenancy permit is impossible when required posture evidence is stale, unauthenticated, or from a previous boot unless an explicitly approved degraded policy says otherwise.
- [ ] Operators can determine exactly when and how each posture value was observed.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 11. Node/collector authentication or attestation chain

**Severity:** BLOCKER  
**Related controls:** C023, C044, C048  
**Audit basis:** A caller can supply mitigation state; no node identity/attestation validation exists in this package.  
**Objective:** Authenticate the node and collector and bind mitigation observations to a verifiable identity/attestation chain before they influence security policy.

### Required deliverables

- [ ] Node identity mechanism and trust roots.
- [ ] Collector attestation/signature format.
- [ ] Verification library/path integrated before state acceptance.

### Architecture and implementation checklist

- [ ] Choose node identity appropriate to deployment (TPM-backed key, workload identity, cloud instance identity, SPIFFE/SVID, or equivalent) and document trust assumptions.
- [ ] Bind observations to node identity, boot/session nonce, collector version/digest, timestamp/age, and payload digest.
- [ ] If hardware attestation is used, define PCR/measurement policy, nonce freshness, verifier trust roots, and acceptable firmware/boot states.
- [ ] Reject replayed, expired, mismatched-node, unknown-root, revoked, or invalidly signed observations.
- [ ] Rotate node/collector credentials without silently accepting unsigned fallback.
- [ ] Separate collector signing authority from scheduler/consumer authorization.
- [ ] Expose attestation verification status and reason codes without leaking sensitive claims.
- [ ] Define safe behavior when verifier/identity services are unavailable: normally fail closed for cross-tenant placement.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Replay, signature-tamper, wrong-node, expired-cert, revoked-root, nonce-reuse, and downgrade tests.
- [ ] Test rotation overlap and rollback resistance.
- [ ] Hardware/cloud attestation integration tests on every supported provider/edge mode.
- [ ] Retain verification result and certificate/attestation reference in evidence.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] BLOCKER: no remote or external node posture is trusted without successful identity/attestation verification.
- [ ] Trust-root changes are auditable, reviewed, and reversible.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 12. Authorization and least-privilege capability model for recording/querying posture

**Severity:** HIGH  
**Related controls:** C024, C042, C043  
**Audit basis:** No identities, roles, capabilities, or authority checks are implemented.  
**Objective:** Enforce least-privilege authorization for who may record, read, evaluate, override, or administer transient-execution posture and policy.

### Required deliverables

- [ ] Capability/RBAC/ABAC model.
- [ ] Authorization middleware/library.
- [ ] Permission matrix and audit coverage.

### Architecture and implementation checklist

- [ ] Enumerate operations: collect/submit posture, query posture, evaluate co-tenancy, modify required sets, quarantine node, emergency-disable, approve exception, and read detailed diagnostics.
- [ ] Define principals and capabilities for collector, scheduler, operator, security admin, auditor, CI/release, and read-only monitoring roles.
- [ ] Default deny unknown principals and undeclared actions.
- [ ] Scope permissions by node/site/environment/tenant where required; prevent cross-tenant diagnostic leakage.
- [ ] Separate policy-authoring from policy-approval and emergency actions where segregation of duties applies.
- [ ] Authorize the consumer of attestation results separately from the producer of observations.
- [ ] Audit every privileged mutation/override with actor, reason, request ID, old/new value, and authorization decision.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Positive/negative permission matrix tests for every operation and role.
- [ ] Privilege-escalation tests for confused deputy, scope widening, forged role claims, and stale credentials.
- [ ] Verify no ordinary API path can write authoritative state without collector capability.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] All privileged boundaries have explicit authentication + authorization checks before side effects.
- [ ] Authorization failures return stable machine-readable codes and generate security audit events.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 13. Workload trust-class policy source and authoritative mapping to required mitigations

**Severity:** HIGH  
**Related controls:** C006, C011, C019, C046  
**Audit basis:** 4.2.0 can evaluate a caller-provided required set, but it does not own or validate the policy that derives that set from workload trust class.  
**Objective:** Create an authoritative workload trust-class policy that deterministically derives the required mitigation set for each placement decision.

### Required deliverables

- [ ] Versioned trust-class taxonomy.
- [ ] Policy data/schema mapping classes/tier/environment to required mitigations and SMT rules.
- [ ] Policy distribution/approval mechanism.

### Architecture and implementation checklist

- [ ] Define trust classes using observable attributes rather than ad-hoc caller strings: tenant relationship, workload sensitivity, isolation tier, regulatory/security class, and execution-plane constraints.
- [ ] Specify precedence when workload, tenant, environment, site, cost, and isolation-tier rules conflict; security requirements must not be weakened implicitly by cost.
- [ ] Define baseline and stricter mitigation sets, including behavior for future/unknown mitigation names.
- [ ] Bind policy version/digest to each decision and expose it in explain/evidence output.
- [ ] Validate inputs from SCH-01/PLN-04 and reject unknown trust classes or unmapped combinations.
- [ ] Support controlled policy rollout, rollback, and staged evaluation.
- [ ] Prevent untrusted workloads from self-declaring a lower trust requirement.
- [ ] Document same-tenant exceptions and whether sub-tenant/security-domain distinctions require stronger treatment.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Table-driven tests for every trust class and boundary combination.
- [ ] Conflict/precedence tests and unknown-class fail-closed tests.
- [ ] Policy-version compatibility and rollback tests.
- [ ] Integration tests with scheduler and execution-plane metadata sources.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Every cross-tenant decision has a deterministic, authoritative required set; callers cannot arbitrarily weaken it.
- [ ] Policy changes are reviewed, versioned, provenance-bound, and auditable.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 14. Declarative configuration format, schema, secure defaults, site/environment overrides, provenance, activation transaction, and rollback

**Severity:** HIGH  
**Related controls:** C033-C038  
**Audit basis:** No configuration subsystem or configuration provenance exists.  
**Objective:** Implement a secure, declarative, provenance-aware configuration subsystem with validation, atomic activation, environment/site overrides, and rollback.

### Required deliverables

- [ ] Configuration schema and examples.
- [ ] Layering/override rules.
- [ ] Activation transaction and rollback journal.

### Architecture and implementation checklist

- [ ] Separate immutable code/artifacts from mutable configuration and observed node state.
- [ ] Define secure defaults for mitigation requirements, freshness TTLs, SMT/core-scheduling policy, telemetry, limits, and dependencies.
- [ ] Use typed schema validation before activation; reject unknown security-critical fields unless compatibility policy explicitly allows them.
- [ ] Define deterministic precedence for global, environment, site, node-class, and emergency overrides.
- [ ] Attach config ID/version, digest, author, approval, creation time, activation time, and superseded version.
- [ ] Stage validation before commit; activate atomically so partially applied security policy cannot be observed.
- [ ] Persist last-known-good configuration and implement operator/automatic rollback criteria.
- [ ] Protect configuration from ordinary workload write access and secret leakage.
- [ ] Support dry-run/evaluate mode that shows decision deltas before activation.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Schema fuzz/negative tests for malformed, ambiguous, duplicate, out-of-range, and unknown fields.
- [ ] Atomicity tests with crash/failure injected between prepare and commit.
- [ ] Override-precedence and rollback tests.
- [ ] Evidence captures active configuration digest for every verification run.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No invalid or partially applied configuration can become active.
- [ ] Every runtime decision is attributable to an immutable configuration version/digest.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 15. Scheduler/placement integration adapter and refusal propagation

**Severity:** HIGH  
**Related controls:** C003, C021, C030, C083  
**Audit basis:** `SCH-01` is named in the contract, but no integration code or integration test is present.  
**Objective:** Integrate INV-43 with the scheduler/placement layer so unsafe cross-tenant placements are rejected with stable, explainable reasons.

### Required deliverables

- [ ] SCH-01 adapter/contract.
- [ ] Placement filter or admission hook.
- [ ] End-to-end refusal/permit integration tests.

### Architecture and implementation checklist

- [ ] Define the scheduler request shape: node identity, workload/tenant/trust-class metadata, execution tier, request ID, and policy version expectations.
- [ ] Resolve required mitigation set from authoritative policy rather than accepting a caller-weakened list.
- [ ] Fetch/verify current node posture and evaluate `may_cotenant` before placement commit.
- [ ] Map `required_mitigation_missing`, `unsafe_smt`, stale/attestation/policy errors to scheduler-native unschedulable reasons without collapsing them into generic failure.
- [ ] Specify timeout/cancellation/idempotency behavior so retries cannot accidentally commit an unsafe placement.
- [ ] Ensure permit decisions have bounded lifetime and are revalidated if node posture/policy changes before commit.
- [ ] Propagate decision ID and evidence reference into scheduler events.
- [ ] Define behavior during INV-43 outage: fail closed for cross-tenant placements unless an approved same-tenant/degraded mode applies.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] End-to-end tests for safe permit, missing mitigation, unsafe SMT, stale observation, invalid attestation, policy mismatch, timeout, retry, and node-state change between evaluate/commit.
- [ ] Concurrency test multiple simultaneous placements against one node.
- [ ] Verify scheduler surfaces stable operator-readable reasons and does not bypass on adapter failure.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] BLOCKER/HIGH gate remains closed until the scheduler cannot commit a prohibited placement under tested race/failure scenarios.
- [ ] All placement decisions carry a traceable INV-43 decision/evidence identifier.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 16. Hardware capability discovery integration (`GAP-02`)

**Severity:** HIGH  
**Related controls:** C003, C021, C030, C083  
**Audit basis:** Dependency is documented only; no adapter/fixture proves interoperability.  
**Objective:** Integrate GAP-02 hardware capability discovery so available CPU/kernel/virtualization capabilities are consumed as authenticated inputs without being mistaken for active mitigation state.

### Required deliverables

- [ ] Versioned GAP-02 adapter.
- [ ] Capability-to-policy normalization rules.
- [ ] Fixtures for supported architectures/providers.

### Architecture and implementation checklist

- [ ] Define which GAP-02 fields inform applicability/capability (CPU vendor/family/features, microcode availability, core scheduling support) versus which must still come from direct read-back.
- [ ] Version and schema-validate the discovery payload.
- [ ] Authenticate/authorize the source and bind it to node identity.
- [ ] Handle absent/unknown capabilities explicitly; never infer mitigation active solely because hardware supports it.
- [ ] Map hardware capability to collector backend selection and policy applicability.
- [ ] Define cache/freshness and invalidation on hotplug, firmware, hypervisor, or kernel changes.
- [ ] Expose contradictions between discovery and read-back as a diagnostic/security event.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Contract tests using GAP-02 reference fixtures.
- [ ] Negative tests for unsupported CPU, inconsistent node ID, stale discovery, malformed feature sets, and capability/read-back contradiction.
- [ ] Integration tests on representative x86_64/other supported architectures and virtualized environments.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] GAP-02 interoperability is proven with versioned fixtures and live integration evidence.
- [ ] Capability discovery can constrain policy but cannot create an unearned 'active' mitigation claim.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 17. Execution-plane / isolation-tier integration (`PLN-04`)

**Severity:** HIGH  
**Related controls:** C003, C021, C030, C083  
**Audit basis:** Dependency is documented only; there is no tier-to-required-mitigation mapping or integration test.  
**Objective:** Integrate PLN-04 execution/isolation tier information so required mitigations reflect the actual execution boundary and cannot be weakened by tier misclassification.

### Required deliverables

- [ ] PLN-04 adapter and tier taxonomy mapping.
- [ ] Tier-to-required-mitigation policy rules.
- [ ] Cross-tier integration test matrix.

### Architecture and implementation checklist

- [ ] Enumerate supported isolation tiers (process/container, VM/microVM, hardware sandbox, etc.) using authoritative PLN-04 identifiers.
- [ ] Define which transient-execution mitigations and sibling-thread restrictions are mandatory per tier and trust combination.
- [ ] Treat unknown/new tiers as fail-closed until policy is explicitly defined.
- [ ] Bind tier identity/version to each co-tenancy decision and explain output.
- [ ] Prevent workload-controlled fields from overriding authoritative execution-tier classification.
- [ ] Define behavior when workloads migrate or tier changes after initial placement.
- [ ] Document which threats remain shared across each tier despite software isolation.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Table-driven tests for every supported tier × trust-class × SMT/core-scheduling combination.
- [ ] Unknown-tier and version-mismatch negative tests.
- [ ] End-to-end tests with PLN-04 state transitions/migrations.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No cross-tenant permit occurs without a recognized, policy-mapped execution tier.
- [ ] Tier changes trigger re-evaluation before unsafe sharing can continue.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 18. Legacy CPU expansion-path peer integration (`INV-34`)

**Severity:** MEDIUM  
**Related controls:** C003, C030, C083  
**Audit basis:** The peer relationship is declared but not exercised.  
**Objective:** Exercise the declared INV-34 legacy CPU peer relationship and define how masked/legacy CPU features affect mitigation policy and evidence.

### Required deliverables

- [ ] INV-34 interface mapping.
- [ ] Legacy CPU policy table.
- [ ] Integration fixtures/tests.

### Architecture and implementation checklist

- [ ] Identify legacy/expanded CPU feature states that change mitigation applicability, availability, or cost.
- [ ] Define precedence when INV-34 masks a feature while raw hardware discovery/read-back reports it.
- [ ] Version the peer contract and bind records to node identity/boot.
- [ ] Ensure legacy compatibility never silently relaxes security requirements; unsupported mitigation capability should normally result in placement restriction.
- [ ] Expose legacy-path involvement in explain output and performance cost analysis.
- [ ] Document supported legacy CPU boundaries and EOL criteria.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Contract tests for feature masking and contradictory peer inputs.
- [ ] Integration tests on at least one representative legacy-path configuration.
- [ ] Negative tests proving inability to bypass required mitigations through legacy feature flags.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] The declared peer dependency is either proven interoperable or formally removed/re-scoped in the architecture contract.
- [ ] Legacy support has explicit security and lifecycle limits.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 19. Explicit external API/RPC/WIT/event/control-plane transport, if this component is intended to run as a service

**Severity:** HIGH  
**Related controls:** C021-C028  
**Audit basis:** Current implementation is an in-process Python library. Authn/authz, timeout, cancellation, retry, idempotency, backpressure, payload and connection limits are therefore not implemented at a transport boundary.  
**Objective:** If INV-43 crosses a process/host boundary, define a complete production transport contract with authentication, authorization, bounded resources, retries, cancellation, idempotency, and backpressure.

### Required deliverables

- [ ] Service/API/RPC/WIT/event contract and versioned schemas.
- [ ] Transport security/authn/authz profile.
- [ ] Operational limits and failure semantics.

### Architecture and implementation checklist

- [ ] First decide whether a remote boundary is required; if not, record that the public surface is intentionally in-process and mark remote controls not applicable.
- [ ] For a service form, define endpoints for posture ingestion/query, policy evaluation, health/readiness, explain, and operator controls with minimal surface area.
- [ ] Specify request/response size limits, concurrency, connection limits, queue depth, deadlines, and cancellation propagation.
- [ ] Define idempotency keys for retriable mutations and replay protection for signed posture submissions.
- [ ] Use mutually authenticated transport or approved equivalent and explicit caller capabilities.
- [ ] Define bounded retry/backoff only for safe operations; distinguish retryable from terminal errors.
- [ ] Implement server-side backpressure/load shedding before memory/queue exhaustion.
- [ ] Version content types/contracts and include correlation IDs.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Contract/conformance tests for every endpoint and error code.
- [ ] Protocol fuzzing, oversized payload, slowloris/connection exhaustion, cancellation, retry, duplicate-request, and authn/authz tests.
- [ ] Latency/backpressure benchmarks at configured limits.
- [ ] Verify fail-closed behavior when dependency or identity services fail.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No undocumented remote boundary is used in production.
- [ ] If remote, every transport control in C021-C028 is implemented, bounded, tested, and evidenced.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 20. Interface version negotiation and backward/forward compatibility tests

**Severity:** MEDIUM  
**Related controls:** C016, C027, C093  
**Audit basis:** Schemas are versioned, but negotiation rules and compatibility tests are absent.  
**Objective:** Define explicit schema/interface version negotiation and prove backward/forward compatibility across supported peer versions.

### Required deliverables

- [ ] Compatibility policy and matrix.
- [ ] Negotiation algorithm/headers/fields if remote.
- [ ] Golden fixtures for every supported contract version.

### Architecture and implementation checklist

- [ ] State semantic-version or protocol-version rules for `PK_MITIGATIONS`, `PK_COTENANCY`, `PK_ERROR`, policy, evidence, and adjacent adapters.
- [ ] Define additive vs breaking changes and unknown-field behavior.
- [ ] Specify minimum/maximum peer versions and what happens outside the range.
- [ ] For in-process Python APIs, define deprecation periods and import/call compatibility; for remote APIs, define negotiation handshake.
- [ ] Never downgrade security semantics silently; incompatible security fields must fail safely.
- [ ] Maintain translation/adaptation code only where semantics remain equivalent.
- [ ] Record negotiated/effective version in telemetry/evidence.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Replay v1 fixtures against newer validators/consumers and newer additive fixtures against older tolerant consumers where supported.
- [ ] Negative tests for unsupported major versions and security-critical unknown fields.
- [ ] Matrix test minimum/current/maximum supported adjacent versions.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Supported combinations are documented and continuously tested.
- [ ] A version mismatch cannot result in a permissive decision through field loss or defaulting.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 21. Full schema-conformance test runner using a standards validator

**Severity:** MEDIUM  
**Related controls:** C022, C029, C082  
**Audit basis:** Schemas and fixtures are present, but repository tests only guarantee JSON parseability/shape metadata without declaring a JSON Schema validator dependency.  
**Objective:** Turn the included JSON Schemas into an enforced conformance suite using a pinned standards-compliant validator.

### Required deliverables

- [ ] Pinned `jsonschema` dependency/test extra.
- [ ] Positive and negative fixture corpus.
- [ ] Schema conformance test runner.

### Architecture and implementation checklist

- [ ] Validate all bundled schemas against Draft 2020-12 meta-schema.
- [ ] Validate every reference fixture in tests and reject additional/unknown fields according to each contract's compatibility policy.
- [ ] Create negative fixtures for missing required fields, wrong types, NaN/infinity equivalents, invalid identifiers, invalid status values, negative costs, and malformed errors.
- [ ] Add schema IDs/URIs and stable version naming conventions.
- [ ] Validate serializer output from live code against schema, not only static fixtures.
- [ ] Define canonical JSON representation if signatures/digests depend on serialization.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Run schema suite under every supported Python version.
- [ ] Mutation-test fixtures to ensure each important constraint causes failure when violated.
- [ ] Capture validator version and conformance results in release evidence.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] All externally visible JSON emitted by INV-43 validates against its declared schema version.
- [ ] Schema validation is a mandatory release gate, not an optional local tool.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 22. Tamper-evident security audit log / append-only event chain

**Severity:** HIGH  
**Related controls:** C049  
**Audit basis:** No audit-event implementation, signature/hash chain, sink, or retention mechanism exists.  
**Objective:** Implement tamper-evident security auditing for posture changes, policy decisions, privileged actions, and security-relevant failures.

### Required deliverables

- [ ] Versioned audit event schema.
- [ ] Append-only/tamper-evident sink with hash chaining/signing or platform equivalent.
- [ ] Retention/export and verification tooling.

### Architecture and implementation checklist

- [ ] Define event types: observation accepted/rejected, attestation result, policy/config change, co-tenancy permit/refusal, quarantine, emergency disable, privilege change, exception use, gate result.
- [ ] Include event ID, monotonic sequence, timestamp/clock quality, actor/principal, node/site/environment, decision/config/policy digests, previous-event hash, and reason code.
- [ ] Protect event integrity with chained hashes plus periodic signature/checkpoint or an approved immutable log service.
- [ ] Separate security audit from ordinary application logs and restrict write/delete permissions.
- [ ] Define backpressure/failure behavior: security decisions must not silently proceed if mandatory audit durability cannot be met, according to documented mode.
- [ ] Redact tenant-sensitive payloads while preserving stable pseudonymous correlation.
- [ ] Provide verification/export tooling for incident review.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Tamper/delete/reorder/insertion tests prove chain verification fails.
- [ ] Permission tests prevent workload/operator roles from rewriting history.
- [ ] Volume/retention tests and sink outage/failover tests.
- [ ] Evidence includes audit-chain verification at release and incident drill.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Security-sensitive operations produce independently verifiable audit evidence.
- [ ] Audit integrity failure is visible, alertable, and handled according to fail-safe policy.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 23. Supply-chain integrity package: SBOM, artifact digest/signature, provenance/attestation, approved dependency policy

**Severity:** HIGH  
**Related controls:** C045  
**Audit basis:** No SBOM, signature, or provenance/attestation artifacts are present; 4.2.0 includes only an unsigned SHA-256 file manifest.  
**Objective:** Build a complete software supply-chain integrity package that proves what source, dependencies, tools, and artifacts produced each release.

### Required deliverables

- [ ] CycloneDX/SPDX SBOM.
- [ ] Artifact digests/signatures.
- [ ] Build provenance/attestation and dependency-approval record.

### Architecture and implementation checklist

- [ ] Generate SBOM from the locked dependency graph, including optional/release-only tooling used for certification where policy requires.
- [ ] Create cryptographic digests for source archive, wheel/sdist, schemas, policy/config baselines, and evidence bundle.
- [ ] Sign artifacts with organization-approved signing identity or produce verifiable provenance attestation.
- [ ] Record source revision, dirty-tree status, build environment/tool versions, dependency hashes, and build command.
- [ ] Enforce dependency allow/deny policy, vulnerability/license checks, and provenance requirements.
- [ ] Reject unpinned/unapproved packages and unverifiable artifacts in release CI.
- [ ] Verify signatures/digests before deployment and before consuming policy/artifact inputs.
- [ ] Define key rotation/revocation and compromised-build response.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Verify SBOM completeness against installed environment and wheel metadata.
- [ ] Tamper artifact/dependency and prove verification/deployment fails.
- [ ] Rebuild from provenance and compare expected outputs/digests where reproducibility is required.
- [ ] Archive SBOM, signatures, provenance, and scan results with release evidence.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A production artifact is deployable only after provenance and integrity verification succeeds.
- [ ] Unsigned SHA-256 manifest alone is not considered supply-chain attestation.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 24. Formal threat-model document covering malicious tenants, compromised workloads, hostile inputs, supply chain, and control-plane abuse

**Severity:** MEDIUM  
**Related controls:** C041  
**Audit basis:** `contract.py` lists several threats, but not a complete threat model with assets, trust boundaries, assumptions, mitigations, and residual risk.  
**Objective:** Create a formal threat model that drives architecture, controls, adversarial tests, and residual-risk acceptance.

### Required deliverables

- [ ] Threat-model document and data-flow/trust-boundary diagrams.
- [ ] Threat/control/test matrix.
- [ ] Residual-risk and assumption register.

### Architecture and implementation checklist

- [ ] Inventory assets: tenant confidentiality, node posture integrity, policy integrity, scheduler decisions, identities, attestations, audit trail, availability.
- [ ] Map trust boundaries among workload, collector, node OS/kernel/hypervisor, scheduler, policy service, operators, providers, `pk_core`, telemetry/evidence sinks.
- [ ] Model malicious tenant/workload, compromised node, forged collector, hostile API input, replay, stale state, supply-chain compromise, operator misuse, dependency compromise, and denial-of-service.
- [ ] Include microarchitectural threats relevant to shared caches/predictors/buffers/SMT and state clearly which are mitigated vs residual.
- [ ] Use STRIDE/LINDDUN/attack-tree or approved methodology, but tie each threat to concrete controls and tests.
- [ ] Document assumptions such as trusted kernel/hypervisor and implications if violated.
- [ ] Rank risk using organizational method and assign owners/acceptance for residual risk.
- [ ] Review whenever supported hardware, execution tier, transport, or trust boundary changes.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Security review confirms every HIGH threat has mitigation or approved acceptance.
- [ ] Adversarial tests reference threat IDs and evidence is linked in RTM.
- [ ] Tabletop exercise validates detection/containment of at least one forged-posture and one side-channel-related scenario.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No security certification based solely on the short `contract.py` threat list.
- [ ] Threat model is current, versioned, approved, and directly connected to verification evidence.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 25. Adversarial security test suite (privilege escalation, injection, replay, spoofing, escape, side-channel misuse, exhaustion)

**Severity:** HIGH  
**Related controls:** C050, C087  
**Audit basis:** Current negative tests cover policy input/refusal logic only.  
**Objective:** Create adversarial tests that challenge privilege boundaries, identity, protocol/input handling, replay resistance, isolation assumptions, side-channel policy, and resource limits.

### Required deliverables

- [ ] Security test plan derived from threat IDs.
- [ ] Automated adversarial suite.
- [ ] Reproducible evidence and remediation tracking.

### Architecture and implementation checklist

- [ ] Test privilege escalation across collector/scheduler/operator/auditor roles.
- [ ] Test injection in identifiers, structured payloads, logs, config, shell/process boundaries, and any future RPC serialization.
- [ ] Test replay of signed observations, decisions, idempotency keys, and stale policy/config.
- [ ] Test spoofed node/tenant/workload identities and cross-node posture substitution.
- [ ] Test attempts to bypass `required_mitigation_missing` and `unsafe_smt` by malformed/duplicate/Unicode/confusable inputs or version downgrade.
- [ ] Test exhaustion using high-cardinality identifiers, huge required sets, request storms, slow clients, and telemetry amplification.
- [ ] For actual isolation mechanisms, test documented escape/side-channel misuse scenarios without claiming hardware attack coverage that lab setup cannot demonstrate.
- [ ] Run with ordinary and optimized Python to ensure security behavior never relies on `assert`.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Automate high-value tests in CI; run hardware/lab-dependent tests on scheduled or release cadence.
- [ ] Capture seed/input, environment, expected security invariant, result, and evidence digest.
- [ ] Require regression tests for every security defect.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] All threat-model HIGH/critical abuse cases have automated or documented lab tests with pass criteria.
- [ ] A security-test failure blocks certification until fixed or formally risk-accepted.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 26. Fuzzing/property-based testing for identifiers, schemas, required-set handling, and untrusted boundary inputs

**Severity:** HIGH  
**Related controls:** C085  
**Audit basis:** No fuzz harness/corpus/property suite is included.  
**Objective:** Add fuzzing and property-based tests for every untrusted parser/input boundary and core security invariant.

### Required deliverables

- [ ] Hypothesis/property suite.
- [ ] Coverage-guided fuzz targets/corpus where applicable.
- [ ] Crash/minimized-case retention workflow.

### Architecture and implementation checklist

- [ ] Fuzz `_require_identifier` with Unicode, control chars, surrogates, very long strings, confusables, null-like values, and non-string types.
- [ ] Property-test `_normalise_required` for deduplication, order stability, non-empty constraint, unknown future mitigations, generators, and pathological iterables.
- [ ] Fuzz mitigation records for statuses/costs including booleans, huge numbers, NaN/infinity, decimals, custom numeric types, malformed tuples/lists.
- [ ] Fuzz JSON schema payloads and future API protocol handlers.
- [ ] Assert invariants: unknown required mitigation never permits cross-tenant sharing; unsafe SMT never permits; serializer output always schema-valid; exceptions remain bounded/stable.
- [ ] Bound input sizes before fuzzed structures can cause memory blowup.
- [ ] Persist minimized regressions as deterministic unit tests.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Set time/iteration budgets for PR and longer nightly fuzz runs.
- [ ] Track code/path coverage and new corpus discoveries.
- [ ] Run under sanitizers/instrumentation for any native extensions introduced later.
- [ ] Archive failing seeds and proof of fix.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No reproducible crash, hang, invariant violation, or uncontrolled resource blowup remains in supported input domains.
- [ ] Fuzzing becomes a recurring CI/release activity, not a one-time exercise.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 27. Concurrency model, synchronization/thread-safety guarantee, and race tests

**Severity:** HIGH  
**Related controls:** C086  
**Audit basis:** `MitigationState` is mutable and unsynchronized; no single-thread-only contract or concurrency protection is documented/tested.  
**Objective:** Define and enforce the concurrency model for mutable posture/configuration/decision state, then prove absence of races relevant to security decisions.

### Required deliverables

- [ ] Concurrency contract.
- [ ] Synchronization/immutability implementation.
- [ ] Race/stress test suite.

### Architecture and implementation checklist

- [ ] Decide whether `MitigationState` is thread-confined, immutable-snapshot, lock-protected, or replaced by transactional state storage.
- [ ] Prevent torn reads across mitigations, SMT state, core-scheduling state, freshness, and policy version during one authorization decision.
- [ ] Use copy-on-write/immutable snapshots or well-defined locking order for updates.
- [ ] Define atomic version/generation numbers so consumers can detect state changes between evaluate and commit.
- [ ] Avoid holding locks across network/dependency calls.
- [ ] Specify concurrent update semantics for duplicate collectors and out-of-order observations.
- [ ] Document process/distributed concurrency separately from in-process thread safety.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Multi-thread stress tests for record/report/evaluate/update paths.
- [ ] Race test posture change during scheduler decision and ensure stale permit is invalidated.
- [ ] Run repeated tests with forced scheduling/yields and, where useful, process-level concurrency.
- [ ] Static/type review for shared mutable structures.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Concurrency guarantees are explicit and testable; no permit can be based on a mixture of incompatible state generations.
- [ ] If single-thread confinement is chosen, runtime assertions/architecture enforce the confinement rather than relying on convention.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 28. Failure taxonomy plus health/stall detection

**Severity:** HIGH  
**Related controls:** C051, C052, C071  
**Audit basis:** There is no health/readiness state machine or dependency-stall detector.  
**Objective:** Define a failure taxonomy and implement health/readiness/stall detection that distinguishes safe degradation from security-critical inability to authorize placement.

### Required deliverables

- [ ] Failure catalog with stable codes/severity/retryability.
- [ ] Health/readiness state machine.
- [ ] Dependency-stall detectors and thresholds.

### Architecture and implementation checklist

- [ ] Enumerate failures for collector, node, kernel/hypervisor, identity/attestation, policy/config, scheduler link, `pk_core`, audit sink, telemetry sink, storage, time service, site/network/provider.
- [ ] Classify each as success/degraded/retryable/terminal/security-unsafe and define operator action.
- [ ] Expose liveness separately from readiness-to-authorize-cross-tenant placement.
- [ ] Detect stale observations, hung collectors, queue stalls, dependency timeouts, repeated attestation failures, and policy/config mismatch.
- [ ] Use monotonic timers and bounded thresholds; avoid false healthy state when no recent successful observation exists.
- [ ] Tie health state to admission behavior and alerts.
- [ ] Include active version/config/policy/last-observation/last-error in diagnostic health output with safe redaction.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] State-transition tests across healthy→degraded→not-ready→recovered.
- [ ] Inject stalled dependency/collector and verify detection within objective.
- [ ] Verify same-tenant/degraded behavior matches approved policy while cross-tenant remains fail closed when required evidence is unavailable.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Operators and automation can distinguish process-alive from security-ready.
- [ ] No stale or stalled dependency can leave a node falsely eligible indefinitely.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 29. Retry/backoff/jitter policy for future read-back/control-plane operations

**Severity:** MEDIUM  
**Related controls:** C025, C053  
**Audit basis:** No dependency I/O exists yet, so retry semantics remain unspecified.  
**Objective:** Specify bounded retry, exponential backoff, jitter, deadline, and idempotency rules for external I/O without turning uncertainty into repeated unsafe side effects.

### Required deliverables

- [ ] Retry policy per operation class.
- [ ] Reusable retry helper/middleware.
- [ ] Metrics for attempts/exhaustion.

### Architecture and implementation checklist

- [ ] Classify operations as read-only/idempotent, idempotent-with-key, or non-retriable.
- [ ] Set maximum attempts, total deadline, base/max backoff, and full/equal jitter strategy per dependency.
- [ ] Respect caller cancellation/deadline and do not retry past decision validity/freshness windows.
- [ ] Never retry authorization by assuming last known safe state after freshness expires.
- [ ] Use idempotency keys for mutable remote operations such as posture submission/config activation/quarantine where applicable.
- [ ] Reset/circuit-break retries during persistent dependency failure to avoid cascades.
- [ ] Emit retry reason and attempt count without log storms.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Deterministic tests with fake clock/randomness for backoff bounds.
- [ ] Timeout/cancellation tests and duplicate-side-effect tests.
- [ ] Dependency recovery tests after retry exhaustion/circuit-open state.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Retries are bounded, observable, and only applied where semantics are safe.
- [ ] Retry behavior cannot extend a security decision beyond its evidence validity window.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 30. Admission control, load shedding/circuit breaking, and bounded resource model

**Severity:** HIGH  
**Related controls:** C017, C054, C067, C069  
**Audit basis:** No queue/concurrency/fan-out limits or saturation model exists.  
**Objective:** Protect INV-43 and adjacent control planes from overload using explicit quotas, admission control, bounded queues/concurrency, load shedding, and circuit breaking.

### Required deliverables

- [ ] Capacity/limit configuration.
- [ ] Admission/backpressure implementation.
- [ ] Saturation metrics and overload policy.

### Architecture and implementation checklist

- [ ] Define maximum request size, required-set cardinality, identifier length, concurrent evaluations, observation ingestion rate, node cardinality, queue depth, and fan-out.
- [ ] Reject or shed excess work before allocating unbounded memory or threads.
- [ ] Prioritize security-critical posture refresh/quarantine over low-priority diagnostics during overload.
- [ ] Use bounded worker pools/queues and document fairness among tenants/sites.
- [ ] Circuit-break failing external dependencies while preserving fail-closed authorization semantics.
- [ ] Define graceful degradation for metrics/audit/export while preserving mandatory security evidence according to policy.
- [ ] Return stable overload/retry-after signals rather than timeouts where possible.
- [ ] Protect high-cardinality telemetry from becoming a secondary exhaustion vector.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Load tests to configured ceilings plus 2×/10× overload.
- [ ] Verify bounded memory, queue, threads, file descriptors, and latency during saturation.
- [ ] Fairness tests across tenants/sites and recovery tests after shedding/circuit breaking.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Resources remain within documented bounds under hostile or accidental overload.
- [ ] Overload never converts an unknown/failed security check into a permit.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 31. Failover/degraded/restart/replay/split-brain semantics

**Severity:** HIGH  
**Related controls:** C014, C018, C055-C058  
**Audit basis:** The in-memory model has no distributed lifecycle or documented stateless-reconstruction contract.  
**Objective:** Define safe lifecycle semantics for restart, failover, replay, degraded mode, and distributed ownership so stale or duplicate state cannot authorize unsafe placement.

### Required deliverables

- [ ] Lifecycle/state-reconstruction design.
- [ ] Leader/ownership or stateless model definition.
- [ ] Restart/failover runbooks and tests.

### Architecture and implementation checklist

- [ ] Decide whether service state is reconstructable from authoritative collectors/policy or persisted; document source of truth for each field.
- [ ] On restart, mark posture unknown until fresh authenticated observations are obtained unless persisted evidence validity is explicitly proven.
- [ ] Define duplicate collector/controller ownership and fencing/version rules.
- [ ] Protect against stale controller decisions after failover with epochs/leases/generation IDs.
- [ ] Define network partition behavior: which side may authorize, and under what evidence freshness conditions.
- [ ] Prevent replay of pre-restart/pre-boot observations.
- [ ] Specify recovery ordering among config, policy, identity trust, posture collection, scheduler readiness, and audit.
- [ ] Define degraded operation only for noncritical dependencies and keep security checks fail closed.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Crash at every lifecycle phase and verify safe reconstruction.
- [ ] Leader/failover/partition tests for duplicate ownership and stale epochs.
- [ ] Restart with stale persisted/cached posture and confirm no unsafe permit.
- [ ] Recovery objective measurements for documented RTO/RPO-like goals.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A restart/failover cannot inherit unjustified 'safe' state.
- [ ] Distributed ownership has explicit fencing or the architecture is proven stateless/single-owner.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 32. Quarantine/freeze/disable/emergency-control implementation

**Severity:** HIGH  
**Related controls:** C059, C092  
**Audit basis:** Policy refusal exists, but no operator control plane for quarantining unsafe nodes or globally disabling placement is supplied.  
**Objective:** Provide audited operator controls to quarantine unsafe nodes, freeze decision changes, disable cross-tenant placement, and enact emergency policy without code changes.

### Required deliverables

- [ ] Quarantine/disable control API or command.
- [ ] Emergency policy/config mechanism.
- [ ] Audit and rollback path.

### Architecture and implementation checklist

- [ ] Define node states such as active, quarantined, draining, disabled, and investigation-hold with legal transitions.
- [ ] Quarantine must immediately make the node ineligible for new cross-tenant placement and optionally trigger scheduler drain according to integration policy.
- [ ] Implement global/site/node emergency disable with least privilege and multi-party approval where required.
- [ ] Require reason, ticket/incident reference, actor, timestamp, and expiry/review for temporary controls.
- [ ] Make controls idempotent and resilient to partial failure.
- [ ] Ensure a compromised node cannot self-clear quarantine.
- [ ] Expose control state in health/explain/telemetry and tamper-evident audit logs.
- [ ] Provide safe rollback/unquarantine only after fresh posture/attestation verification.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] End-to-end tests proving quarantine blocks placement immediately.
- [ ] Permission/abuse tests for unauthorized clear/disable.
- [ ] Failure-injection tests during quarantine propagation.
- [ ] Operator drill for emergency global disable and recovery.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] HIGH gate remains closed until unsafe nodes can be removed from eligibility without deploying new code.
- [ ] Every emergency action is attributable, reversible, and evidenced.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 33. Fault-injection and disaster/partition/reconnect tests

**Severity:** HIGH  
**Related controls:** C060, C089  
**Audit basis:** No chaos/fault harness or recovery-objective evidence exists.  
**Objective:** Prove recovery behavior under real failure modes using repeatable fault injection, partition, disaster, reconnect, and degraded-control-plane tests.

### Required deliverables

- [ ] Fault-injection harness/scenarios.
- [ ] Recovery objectives.
- [ ] Automated evidence reports.

### Architecture and implementation checklist

- [ ] Inject collector crash/hang, attestation verifier failure, policy/config unavailable, scheduler disconnect, audit sink outage, clock skew, node reboot, stale cache, partial network partition, duplicate controller, provider outage, and corrupted input/state.
- [ ] Define expected safety invariant and recovery objective for each fault before running the test.
- [ ] Exercise reconnect with queued/out-of-order observations and ensure stale generations are rejected.
- [ ] Test recovery from site isolation and later reconciliation without split-brain permits.
- [ ] Include dependency latency and packet loss, not only hard failures.
- [ ] Measure time to not-ready/quarantine and time to safe recovery.
- [ ] Automate environment cleanup so tests are repeatable and non-destructive.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Run fault suite on PR subset and full release/nightly cadence.
- [ ] Verify no injected fault yields cross-tenant permit without valid current evidence.
- [ ] Archive scenario, seed, environment, observed transitions, and timing evidence.
- [ ] Create regression scenarios for every production incident.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Documented recovery objectives are met or exceptions are formally accepted.
- [ ] Safety invariants hold throughout failure and recovery, not just after steady state returns.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 34. Reproducible performance benchmark harness and measured baseline

**Severity:** HIGH  
**Related controls:** C061, C063, C064, C088  
**Audit basis:** Cost values are caller-provided; the repository does not measure mitigation overhead itself.  
**Objective:** Measure actual mitigation overhead with a reproducible benchmark harness instead of accepting caller-provided cost percentages as ground truth.

### Required deliverables

- [ ] Benchmark harness and workload suite.
- [ ] Raw result schema and environment fingerprint.
- [ ] Baseline dataset per mitigation/platform.

### Architecture and implementation checklist

- [ ] Define micro/macro workloads sensitive to relevant mitigation costs (syscall/context-switch/I/O/compute/memory/VM-exit patterns as applicable).
- [ ] Measure baseline with controlled mitigation posture and one-or-more mitigation configurations using authoritative read-back to confirm state.
- [ ] Record CPU model/stepping, microcode, kernel, hypervisor, BIOS/SMT/core-scheduling, power governor, topology, memory, runtime, and background-load controls.
- [ ] Calculate overhead with repeated trials, confidence intervals/noise controls, and explicit warmup.
- [ ] Separate per-mitigation estimates from interaction effects; do not blindly sum independent costs if measurements are non-additive.
- [ ] Define how measured results are associated with node class and freshness/version.
- [ ] Feed trusted benchmark results into policy/reporting rather than arbitrary caller input where production cost visibility is required.
- [ ] Store raw data as well as summarized percent values.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Repeatability test across runs and representative nodes.
- [ ] Detect invalid benchmark conditions such as thermal throttling, frequency scaling instability, or changed mitigation state.
- [ ] Compare harness results to known sanity ranges without hard-coding vendor claims as truth.
- [ ] Archive commands, raw data, environment manifest, and analysis script.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] HIGH gate: production 'measured cost' claims must be traceable to reproducible measurements for the relevant node class.
- [ ] Benchmark methodology and uncertainty are documented; cost is not user-supplied unverified metadata.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 35. Approved p50/p95/p99/worst-case thresholds plus performance-regression release gate

**Severity:** HIGH  
**Related controls:** C062, C070  
**Audit basis:** No threshold file, benchmark history, or regression gate is present.  
**Objective:** Define approved latency/throughput/startup/density thresholds and make regressions release-blocking with statistically defensible comparison rules.

### Required deliverables

- [ ] Performance SLO/threshold file.
- [ ] Historical baseline store.
- [ ] Regression gate integrated into release CI.

### Architecture and implementation checklist

- [ ] Define p50/p95/p99/worst-case objectives for policy evaluation, posture refresh, adapter calls, and service endpoints if any.
- [ ] Define throughput/concurrency, startup/readiness, memory/density, and mitigation-overhead ceilings.
- [ ] Segment thresholds by supported platform/tier where hardware differences are material.
- [ ] Specify sample size, warmup, outlier policy, noise budget, and allowed regression percentage/absolute delta.
- [ ] Use a stable benchmark environment or calibrated comparison to reduce false regressions.
- [ ] Require security-preserving performance behavior: no threshold may be met by skipping validation/attestation/audit.
- [ ] Provide override process with owner, justification, expiry, and evidence.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Run benchmark gate against current baseline on every release candidate.
- [ ] Test gate sensitivity with an intentional regression.
- [ ] Track trend data and alert before saturation/regression reaches hard limits.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Release fails when an approved threshold is exceeded without an explicit time-bounded waiver.
- [ ] Threshold changes themselves require review and are versioned/audited.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 36. CPU/memory/storage/network/power/thermal capacity model, including edge-node measurements

**Severity:** MEDIUM  
**Related controls:** C061, C067-C069  
**Audit basis:** No resource or power/thermal measurement suite is supplied.  
**Objective:** Model CPU, memory, storage, network, power, and thermal resource use—including constrained edge nodes—so capacity and safety behavior are predictable.

### Required deliverables

- [ ] Resource/capacity model.
- [ ] Edge measurement profiles.
- [ ] Saturation thresholds/signals.

### Architecture and implementation checklist

- [ ] Measure steady and peak CPU per evaluation/collection cycle, resident memory per tracked node/policy set, storage growth for evidence/audit, and network volume for remote boundaries.
- [ ] Quantify collector cost and benchmark load separately from ordinary policy evaluation.
- [ ] Measure power draw, thermal headroom, frequency throttling, and battery/energy impact on representative far-edge hardware where applicable.
- [ ] Define scaling equations/empirical curves for node count, observation rate, tenant/workload cardinality, and telemetry volume.
- [ ] Set hard caps for caches, evidence buffers, queues, and retained high-cardinality labels.
- [ ] Identify resource contention with scheduler/host workloads and reserve budgets where needed.
- [ ] Document unsupported edge profiles that cannot meet freshness/security objectives.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Run profiling under idle, steady, burst, overload, and recovery conditions.
- [ ] Thermal soak tests confirm collector/benchmark activity does not destabilize the node.
- [ ] Validate capacity predictions against measured scale points.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Capacity model predicts saturation before service/security objectives are violated.
- [ ] Edge deployment is allowed only on hardware profiles with measured resource and thermal margin.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 37. Runtime metrics emitter for rate/errors/latency/saturation/backlog/resources

**Severity:** HIGH  
**Related controls:** C071, C072  
**Audit basis:** Contract names signals but no metrics backend/exporter exists.  
**Objective:** Emit production metrics for health, decisions, errors, latency, saturation, backlog, freshness, dependency state, and resource consumption without unbounded cardinality.

### Required deliverables

- [ ] Metrics specification and exporter.
- [ ] Cardinality budget.
- [ ] SLO/alert recording rules.

### Architecture and implementation checklist

- [ ] Define counters for permit/refusal by stable reason, observation/attestation failures, config/policy activation, quarantine actions, and dependency errors.
- [ ] Define histograms for evaluation latency, collection latency, observation age, dependency latency, and queue wait.
- [ ] Define gauges for ready nodes, stale nodes, unsafe SMT nodes, queue depth, active workers, cache size, audit backlog, and resource use.
- [ ] Use bounded labels; never put raw tenant/workload IDs in standard metric labels if cardinality/privacy risk is high.
- [ ] Export component/version/config/policy identity through info metric or resource attributes.
- [ ] Define scrape/export failure behavior and avoid blocking security decisions on non-mandatory metrics delivery.
- [ ] Document units, aggregation semantics, reset behavior, and expected ranges.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Unit tests verify metric increments and label constraints for each decision/error path.
- [ ] Load test cardinality and exporter backpressure.
- [ ] Dashboards/alerts consume the same stable metric names tested in CI.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Metrics allow operators to distinguish healthy policy rejection from component/dependency failure.
- [ ] Metric emission stays within documented cardinality and performance budgets.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 38. Structured logs with stable node/tenant/workload/operation IDs and redaction/privacy policy

**Severity:** HIGH  
**Related controls:** C073, C075, C079  
**Audit basis:** No logging implementation or telemetry policy exists.  
**Objective:** Implement structured, privacy-aware logs with stable correlation identifiers and explicit redaction rules.

### Required deliverables

- [ ] Logging schema/specification.
- [ ] Structured logger integration.
- [ ] Redaction/privacy policy and tests.

### Architecture and implementation checklist

- [ ] Emit JSON/structured fields for component/version, operation, request/decision ID, node/site/environment, policy/config digest, reason code, dependency, and severity.
- [ ] Use pseudonymous/bounded tenant/workload identifiers where full values are not necessary; never log secret material, tokens, attestation private data, or arbitrary untrusted payloads.
- [ ] Normalize/control untrusted strings to prevent log injection and terminal/control-character abuse.
- [ ] Define which fields may be high cardinality and their retention/export restrictions.
- [ ] Correlate logs to audit events without treating mutable logs as tamper-evident audit.
- [ ] Rate-limit repetitive failures and include suppression counters to avoid log-based denial of service.
- [ ] Define retention, access control, deletion, and privacy handling.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Golden log tests for permit/refusal/error/config/quarantine paths.
- [ ] Secret/redaction tests using canary secret values.
- [ ] Injection tests with control chars/newlines/Unicode confusables.
- [ ] Load test log volume under rejection storm.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Operators can trace a decision without exposing sensitive tenant/secret data.
- [ ] Logging cannot be used to forge records or cause unbounded resource growth.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 39. Distributed trace propagation/correlation

**Severity:** MEDIUM  
**Related controls:** C074, C078  
**Audit basis:** No trace-context support exists.  
**Objective:** Propagate distributed trace context across scheduler, INV-43, collectors, identity/attestation, policy, and audit/telemetry boundaries where tracing is applicable.

### Required deliverables

- [ ] Trace propagation standard/profile.
- [ ] Instrumentation for relevant spans.
- [ ] Sampling/privacy policy.

### Architecture and implementation checklist

- [ ] Adopt approved W3C Trace Context/OpenTelemetry or equivalent.
- [ ] Create spans for placement evaluation, posture retrieval, attestation verify, policy resolve, config access, and downstream decision response.
- [ ] Preserve request/decision IDs even when traces are unsampled.
- [ ] Do not put secrets or raw tenant-sensitive payloads in span attributes.
- [ ] Define trace propagation across async queues/events and retry attempts.
- [ ] Mark security refusal reason and dependency errors with stable low-cardinality attributes.
- [ ] Correlate trace with release/config/policy/observation generations.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Integration tests verify parent/child continuity across each boundary.
- [ ] Sampling tests ensure critical error traces can be retained according to policy without exploding volume.
- [ ] Privacy review of span attributes.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A multi-component placement decision can be followed end-to-end with consistent correlation IDs.
- [ ] Tracing is bounded and does not become a dependency for authorization correctness.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 40. Operator explain surface linking a decision to inputs, policy, topology, and release lineage

**Severity:** MEDIUM  
**Related controls:** C076-C078  
**Audit basis:** Errors now contain reasons, but there is no operator-facing explain endpoint/view or infrastructure/release correlation.  
**Objective:** Provide an operator explain surface that reconstructs why a decision occurred from trusted inputs, policy, topology, and release/config lineage.

### Required deliverables

- [ ] Versioned explain contract/CLI/UI endpoint.
- [ ] Decision record store or reconstructable evidence reference.
- [ ] Redaction/access-control rules.

### Architecture and implementation checklist

- [ ] For each decision expose permit/refusal, stable reason code, node posture generation, required mitigation set and its policy source, SMT/core-scheduling state, observation freshness/attestation status, execution tier, relevant topology, and config/policy/release digests.
- [ ] Distinguish observed facts from derived policy conclusions.
- [ ] Show missing/unknown mitigations explicitly without implying an unobserved state.
- [ ] Link to scheduler request/decision ID and audit/evidence record.
- [ ] Restrict tenant/workload detail based on operator capability and privacy policy.
- [ ] Define retention for explain data and behavior when source evidence has expired.
- [ ] Keep the explain surface read-only; it must not mutate policy/state.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Golden explain tests for all refusal codes and permit paths.
- [ ] Cross-tenant authorization tests prevent one tenant from viewing another's sensitive details.
- [ ] Reconstruction test compares explain output against the exact inputs used at decision time.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] An operator can answer 'why was this workload refused/permitted on this node?' from immutable/reconstructable evidence.
- [ ] Explain output never substitutes guessed current state for the historical decision inputs.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 41. Dashboards and alerts separating load, degradation, policy rejection, dependency failure, attack, and software defect

**Severity:** MEDIUM  
**Related controls:** C080  
**Audit basis:** No dashboard/alert definitions are supplied.  
**Objective:** Create operational dashboards and alerts that separate expected policy enforcement from degradation, dependency failure, attack signals, and software defects.

### Required deliverables

- [ ] Dashboard-as-code definitions.
- [ ] Alert rules with severity/runbook links.
- [ ] SLO/error-budget views.

### Architecture and implementation checklist

- [ ] Dashboard health/readiness, decision volume, refusal reasons, stale/unsafe nodes, observation age, attestation failures, dependency latency/error, queue saturation, resource use, audit backlog, and release/config versions.
- [ ] Separate policy rejections (healthy enforcement) from internal errors and unavailable dependencies.
- [ ] Define attack-oriented alerts for spikes in spoof/replay/authz failures, repeated malformed inputs, and anomalous quarantine events.
- [ ] Define software-defect alerts for exceptions, schema failures, invariant violations, and crash loops.
- [ ] Use multi-window/burn-rate alerting for SLOs where appropriate and avoid paging on normal policy refusal volume unless threshold/anomaly indicates incident.
- [ ] Attach runbook URL/ID and ownership to every page-worthy alert.
- [ ] Version dashboard/alert definitions with repository or deployment config.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Replay synthetic metric fixtures to verify every alert fires/clears as designed.
- [ ] Run alert-routing test to on-call and confirm dedup/suppression behavior.
- [ ] Review cardinality/query cost at fleet scale.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Operators can quickly tell load, policy rejection, dependency failure, attack, and defect apart.
- [ ] Every actionable alert has a tested runbook and owner.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 42. Integration tests with all supported adjacent layers

**Severity:** HIGH  
**Related controls:** C030, C083  
**Audit basis:** Only local unit/conformance adapter tests exist.  
**Objective:** Build integration tests across every supported adjacent layer so the local policy model is proven in the actual architecture, not only in isolation.

### Required deliverables

- [ ] Integration test environment/harness.
- [ ] Contract fixtures/stubs for GAP-02, SCH-01, PLN-04, INV-34, `pk_core`, identity/attestation, config/policy, and telemetry/audit as applicable.
- [ ] End-to-end evidence report.

### Architecture and implementation checklist

- [ ] Define supported integration combinations and test ownership for each boundary.
- [ ] Test authenticated posture collection → policy resolve → `MitigationState` evaluation → scheduler refusal/permit → audit/telemetry.
- [ ] Exercise same-tenant, cross-tenant safe, missing mitigation, unknown future mitigation, unsafe SMT, stale observation, invalid attestation, unsupported tier, and dependency outage.
- [ ] Use versioned real fixtures or ephemeral test services rather than hand-waved mocks for critical contract behavior.
- [ ] Validate error propagation and no fail-open conversion across adapters.
- [ ] Test cancellation/retry/idempotency/resource limits at boundaries.
- [ ] Run on at least one representative real node/provider configuration in release certification.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Automated suite in CI with hermetic dependency versions.
- [ ] Nightly/release job for hardware/provider-dependent integrations.
- [ ] Evidence maps each adjacent-layer contract to passing tests and versions.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] HIGH gate remains closed until every declared supported adjacent layer has passing integration evidence.
- [ ] A declared dependency cannot remain documentation-only while certification says production-ready.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 43. Compatibility test matrix across supported CPU architectures, kernels/runtimes, hypervisors, providers, and protocol versions

**Severity:** HIGH  
**Related controls:** C084, C093  
**Audit basis:** No supported-platform matrix or compatibility lab evidence is present.  
**Objective:** Define and continuously validate a compatibility matrix across CPU architectures, kernels/runtimes, hypervisors/providers, Python/`pk_core`, and protocol/schema versions.

### Required deliverables

- [ ] Supported-platform matrix with lifecycle dates.
- [ ] Automated compatibility jobs/lab plan.
- [ ] Known limitation/EOL records.

### Architecture and implementation checklist

- [ ] Enumerate CPU vendor/family/architecture support, including virtualization exposure nuances.
- [ ] List supported kernel/OS versions, hypervisors, cloud providers/instance classes, edge hardware, Python versions, `pk_core` versions, collector versions, and schema/protocol versions.
- [ ] For each combination state support level: certified, best-effort, unsupported, or planned.
- [ ] Define minimum microcode/kernel prerequisites and provider limitations.
- [ ] Test matrix strategically using equivalence classes while ensuring security-relevant diversity is represented.
- [ ] Add version retirement/EOL dates and migration guidance.
- [ ] Prevent deployment to unsupported combinations through preflight/admission checks where feasible.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Run smoke/conformance on every supported software combination.
- [ ] Run hardware-in-loop tests on representative CPU/hypervisor/provider classes.
- [ ] Negative preflight tests reject known unsupported versions/platforms.
- [ ] Publish evidence date so stale certifications are obvious.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Only matrix entries with current passing evidence are called certified.
- [ ] Unknown platform/version combinations default to unsupported/fail-safe until reviewed.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 44. Soak, burst, overload, scale-out/scale-in, and fleet-scale tests

**Severity:** MEDIUM  
**Related controls:** C063, C088  
**Audit basis:** No load/fleet harness is supplied.  
**Objective:** Validate behavior and resource stability under soak, burst, overload, scale-out/in, and fleet-scale conditions representative of production.

### Required deliverables

- [ ] Load/soak/fleet test harness.
- [ ] Representative workload profiles.
- [ ] Trend and leak-analysis reports.

### Architecture and implementation checklist

- [ ] Define steady-state node count/evaluation rate and peak/burst multipliers.
- [ ] Run multi-hour/day soak appropriate to state/resource leak detection.
- [ ] Exercise rapid node registration/removal, posture refresh waves, scheduler bursts, policy rollout, and recovery after dependency outage.
- [ ] Measure p50/p95/p99/worst-case latency, throughput, queue depth, memory, CPU, file descriptors, telemetry volume, and error/refusal mix.
- [ ] Test fleet cardinality for node/tenant/workload metadata without unbounded caches/labels.
- [ ] Verify fairness and no starvation under multi-tenant load.
- [ ] Observe GC/resource behavior and recovery to baseline after burst/scale-in.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Automate thresholds and leak detection.
- [ ] Run overload beyond capacity to prove admission/load-shedding behavior.
- [ ] Archive environment and raw measurements for reproducibility.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] System stays within approved resource/performance/safety limits for defined fleet scale and duration.
- [ ] Scale tests demonstrate graceful rejection, not unsafe fail-open or uncontrolled growth.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 45. Canary/staged rollout implementation and rollback automation

**Severity:** MEDIUM  
**Related controls:** C038, C092  
**Audit basis:** README contains brief operational guidance only; no rollout/rollback tooling is present.  
**Objective:** Implement canary/staged rollout and automated rollback for code, configuration, policy, collector, and trust-root changes.

### Required deliverables

- [ ] Rollout controller/procedure.
- [ ] Canary health/security metrics and gates.
- [ ] Rollback automation and last-known-good references.

### Architecture and implementation checklist

- [ ] Define rollout stages (lab→canary site/nodes→percentage waves→fleet) and minimum observation period per stage.
- [ ] Pin the exact code/config/policy/collector/trust-root versions advanced together or define compatible independent rollout order.
- [ ] Set automatic stop/rollback criteria for readiness loss, unexpected permit/refusal shifts, attestation failures, stale posture, latency regression, or crash rate.
- [ ] Ensure rollback does not restore expired/revoked trust or unsafe policy; validate compatibility before rollback.
- [ ] Support emergency disable/quarantine independent of rollout system.
- [ ] Record stage approvals, metrics, artifact digests, and rollback reason.
- [ ] Handle mixed-version fleet explicitly using compatibility rules.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Simulate failed canary and confirm rollout halts/rolls back.
- [ ] Test rollback during partial rollout and dependency outage.
- [ ] Verify audit/evidence shows exactly which nodes ran which versions/policies.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No fleet-wide production rollout occurs as a single unobserved step.
- [ ] Rollback path is automated/tested and preserves security invariants.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 46. Backup/restore/migration/reconstruction decision and procedure

**Severity:** MEDIUM  
**Related controls:** C095  
**Audit basis:** Current state is in memory. The repo needs either a formal stateless-reconstruction procedure or persistent-state recovery tooling.  
**Objective:** Decide whether INV-43 is formally stateless/reconstructable or persists state, then provide tested backup/restore/migration/reconstruction procedures accordingly.

### Required deliverables

- [ ] State inventory and classification.
- [ ] Reconstruction or backup/restore design.
- [ ] Migration/versioning procedure.

### Architecture and implementation checklist

- [ ] Classify posture observations, config, policy, trust roots, audit, evidence, decision history, benchmark baselines, and caches by durability requirement.
- [ ] For reconstructable state, define authoritative sources and boot sequence; caches must start unknown until refreshed.
- [ ] For durable state, define storage schema/version, backup frequency, encryption, integrity, retention, and restore validation.
- [ ] Define migration semantics across schema/config versions and rollback compatibility.
- [ ] Protect against restoring stale node posture or revoked identity/trust material.
- [ ] Document RPO/RTO-like objectives for each durable class.
- [ ] Test clean-room rebuild from immutable artifacts + authoritative external sources.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Disaster restore/reconstruction drill.
- [ ] Corrupt/missing backup tests and version migration tests.
- [ ] Verify restored service remains not-ready until security-critical freshness/attestation requirements are re-established.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] C095 has an explicit approved applicability decision and tested procedure.
- [ ] Restoration can never turn historical posture into current authorization evidence without revalidation.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 47. Complete day-0/day-1/day-2 runbook with dependency checks and failure procedures

**Severity:** MEDIUM  
**Related controls:** C096  
**Audit basis:** README is a minimal outline, not an operational runbook.  
**Objective:** Create complete day-0/day-1/day-2 operational runbooks covering bootstrap, deployment, validation, routine operations, dependency failures, policy changes, and recovery.

### Required deliverables

- [ ] Day-0 bootstrap runbook.
- [ ] Day-1 deployment/verification runbook.
- [ ] Day-2 operations/troubleshooting runbook.

### Architecture and implementation checklist

- [ ] Day 0: prerequisites, supported platform preflight, identity/trust bootstrap, dependency installation, config/policy initialization, collector setup, first authoritative observation, readiness criteria.
- [ ] Day 1: build/install artifact verification, canary rollout, `PK_REQUIRE_CORE=1` gate, schema/integration checks, evidence sealing, scheduler enablement.
- [ ] Day 2: health checks, posture freshness, policy/config change procedure, quarantine/unquarantine, rotation, scaling, log/metric interpretation, incident entry points.
- [ ] Include exact commands/API examples with expected safe outputs and stable error codes.
- [ ] Document dependency outage procedures for `pk_core`, attestation, policy, scheduler, audit, and telemetry.
- [ ] Include rollback and emergency-disable steps with permissions/approvals.
- [ ] Link every alert to a specific runbook section.
- [ ] Version runbooks with release and test them in staging.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Operator game-day executes runbook from clean environment without author assistance.
- [ ] Validate commands on Windows and other supported operator environments where applicable.
- [ ] Track runbook defects as release/operations issues.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] A qualified on-call operator can bootstrap, verify, diagnose, quarantine, rollback, and recover INV-43 using documented procedures.
- [ ] README summaries do not substitute for tested operational runbooks.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 48. Incident response plan: severity model, paging, containment, recovery, post-incident evidence

**Severity:** HIGH  
**Related controls:** C097  
**Audit basis:** No incident runbook is present.  
**Objective:** Establish an incident response plan tailored to unsafe placement, forged/stale posture, attestation compromise, side-channel exposure, and service/dependency failure.

### Required deliverables

- [ ] Incident severity model.
- [ ] Paging/escalation matrix.
- [ ] Containment/recovery/evidence/post-incident procedures.

### Architecture and implementation checklist

- [ ] Define severity based on confirmed/possible cross-tenant unsafe co-location, integrity compromise, widespread readiness loss, and degraded non-security functionality.
- [ ] Specify automatic/manual paging triggers and accountable incident roles.
- [ ] Containment actions include global/site/node cross-tenant disable, quarantine, scheduler drain, trust-root revocation, policy freeze, and evidence preservation.
- [ ] Define forensic evidence collection: audit chain, decisions, posture/attestation records, config/policy/release lineage, scheduler events, node/kernel/microcode data.
- [ ] Define recovery prerequisites and re-enable criteria requiring fresh trusted posture.
- [ ] Establish communications and stakeholder/legal/security escalation according to organization policy.
- [ ] Require post-incident root cause, security impact, corrective actions, regression tests, and control updates.
- [ ] Define evidence retention/legal hold handling where applicable.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Tabletop scenarios: false-safe posture, signing key compromise, unsafe SMT rollout, provider/kernel regression, scheduler bypass.
- [ ] Measure paging and containment time against support objectives.
- [ ] Verify emergency controls and evidence export work during drill.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] HIGH gate requires an approved, exercised incident plan with current contacts.
- [ ] Production re-enable after a security incident requires explicit criteria and fresh evidence, not just process restart.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 49. Recurring access/policy/dependency/configuration/architecture review schedule and evidence

**Severity:** MEDIUM  
**Related controls:** C098  
**Audit basis:** No review cadence, owner, or recorded review artifact is supplied.  
**Objective:** Institute recurring governance reviews for access, policy, dependencies, configuration, architecture, and supported-platform risk.

### Required deliverables

- [ ] Review calendar/cadence.
- [ ] Standard review checklist and evidence template.
- [ ] Findings/remediation tracker.

### Architecture and implementation checklist

- [ ] Set cadence based on risk—e.g. quarterly access/policy/dependency review and at least annual architecture review, plus event-driven review after major changes/incidents.
- [ ] Review privileged identities/capabilities and remove stale access.
- [ ] Review required mitigation policy against new disclosures/kernel/vendor guidance and supported workload tiers.
- [ ] Review dependency versions/vulnerabilities/licenses/EOL including `pk_core` and schema validator.
- [ ] Review config defaults/overrides/exceptions for drift and expired emergency settings.
- [ ] Review compatibility matrix and deprecate unsupported hardware/software.
- [ ] Review threat model and ADR assumptions for new trust boundaries.
- [ ] Record approvers, findings, due dates, and closure evidence.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Automate reminders and stale-review detection where governance tooling supports it.
- [ ] Sample previous findings and verify remediation actually landed.
- [ ] Release gate checks for overdue critical reviews according to policy.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] There is auditable evidence of recurring reviews and closed findings.
- [ ] No indefinite emergency override, stale access, or unsupported dependency persists unnoticed.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 50. Exception/waiver/technical-debt/deprecation ledger with owners and expirations

**Severity:** MEDIUM  
**Related controls:** C099  
**Audit basis:** No exception ledger is present.  
**Objective:** Track every exception, waiver, technical-debt item, and deprecated behavior with explicit risk ownership and expiration.

### Required deliverables

- [ ] Machine-readable exception/debt ledger.
- [ ] Approval workflow.
- [ ] Expiry enforcement/reporting.

### Architecture and implementation checklist

- [ ] Give each item an ID, type, affected control/component/version, rationale, risk, compensating controls, owner, approver, creation date, expiry/review date, and remediation link.
- [ ] Prohibit permanent security waivers without periodic reapproval; require expiry by default.
- [ ] Link exceptions into RTM, release evidence, and explain/operations where they change behavior.
- [ ] Distinguish accepted risk from missing evidence; do not mark a control satisfied solely because a waiver exists.
- [ ] Track deprecated APIs/policy fields with removal version/date and migration path.
- [ ] Alert on approaching expiry and fail release when a blocking waiver is expired.
- [ ] Require closure evidence rather than deleting historical records.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] CI parses ledger and rejects malformed/expired required entries.
- [ ] Audit sample verifies production behavior matches compensating controls.
- [ ] Test deprecated-path warnings/removal gates.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] Every unresolved production gap has a visible owner and time-bounded disposition.
- [ ] Expired waivers cannot silently keep the production gate green.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 51. Vulnerability response, patching, and end-of-life SLA

**Severity:** HIGH  
**Related controls:** C094  
**Audit basis:** No SECURITY/patch/EOL policy is supplied.  
**Objective:** Define vulnerability intake, triage, remediation, disclosure/communication, patch cadence, and supported-version end-of-life commitments.

### Required deliverables

- [ ] `SECURITY.md` or equivalent policy.
- [ ] Patch/vulnerability SLA table.
- [ ] Supported/EOL version policy and contact path.

### Architecture and implementation checklist

- [ ] Define private vulnerability reporting channel and expected acknowledgement.
- [ ] Classify severity using approved methodology and include hardware/kernel/provider advisories that affect mitigation correctness.
- [ ] Set remediation/release targets by severity and emergency patch process.
- [ ] Define dependency vulnerability scanning and triage for runtime/build/test dependencies.
- [ ] Define supported release branches, backport policy, and EOL dates/notice period.
- [ ] Specify coordinated handling when mitigation guidance changes due to new transient-execution classes.
- [ ] Define revocation/rollback when a patch or microcode introduces regressions.
- [ ] Link vulnerability fixes to tests, SBOM/provenance, release notes, and incident process when exposure occurred.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Exercise a mock critical advisory from intake to patched signed artifact.
- [ ] Verify unsupported/EOL versions are rejected or clearly flagged by deployment preflight.
- [ ] Track SLA attainment as governance evidence.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] HIGH gate: production has a published internal/external vulnerability path and time-bounded patch commitments.
- [ ] Security fixes are traceable to signed artifacts and regression tests.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## 52. Licensing/NOTICE metadata for redistribution

**Severity:** MEDIUM  
**Related controls:** Outside the 100-item checklist  
**Audit basis:** No license file or redistribution terms are included in the supplied archive.  
**Objective:** Add explicit redistribution licensing and notices so the package can be legally consumed, built, and redistributed under known terms.

### Required deliverables

- [ ] Top-level `LICENSE` file.
- [ ] `NOTICE` file if required by chosen license/dependencies.
- [ ] Package metadata and third-party license inventory.

### Architecture and implementation checklist

- [ ] Obtain owner/legal approval for the intended license; do not infer a license from other repositories.
- [ ] Add exact license text and copyright/attribution information.
- [ ] Populate `pyproject.toml` license metadata and classifiers consistently.
- [ ] Inventory third-party runtime/build/test dependencies and preserve required notices/attributions.
- [ ] Check bundled schemas/fixtures/sample data for external licensing obligations.
- [ ] Document contribution/licensing policy if external contributions are accepted.
- [ ] Include license/notice in built distributions and source archives.
- [ ] Add automated license-compliance scanning appropriate to organizational policy.
- [ ] Assign stable artifact/test/evidence identifiers and link them to the applicable control IDs in the requirements traceability matrix.
- [ ] Document security assumptions, unsupported cases, failure semantics, and operator-visible reason codes introduced by this component.

### Verification and evidence checklist

- [ ] Build wheel/sdist and verify license/notice files are present.
- [ ] Run dependency license scan and review unknown/incompatible results.
- [ ] Check README/release artifacts reference the correct license without contradiction.
- [ ] Run verification from a clean environment with declared dependencies only; capture tool/runtime versions and the exact source/artifact digest.
- [ ] Add at least one negative/failure-path test proving the component fails safely rather than silently skipping or defaulting to a permissive state.
- [ ] Store machine-readable results under the release evidence/conformance hierarchy and seal or digest-bind them to the release artifact.

### Definition of done / release gate

- [ ] No redistribution or external publication until licensing terms are explicitly approved and packaged.
- [ ] License metadata, repository files, and built artifacts agree.
- [ ] Documentation, configuration examples, runbooks, schemas, tests, and deployed behavior agree; no stale claim remains in README/AUDIT_REPORT.
- [ ] Component status is changed from missing only after evidence is independently reproducible and referenced by the production exit gate.

---

## Final production exit checklist

- [ ] All 52 items are either complete with evidence or explicitly marked not-applicable/waived through the approved governance path.
- [ ] All BLOCKER and applicable HIGH items are complete; no production certification relies on skipped tests or absent external dependencies.
- [ ] `PK_REQUIRE_CORE=1` verification passes with the approved pinned `pk_core` version.
- [ ] Standalone verification passes in normal and optimized (`python -O`) modes.
- [ ] All schemas, fixtures, interface compatibility tests, integration tests, adversarial tests, fuzz tests, concurrency tests, fault-injection tests, benchmarks, and rollout/rollback tests required by the supported architecture pass.
- [ ] Authoritative node posture is authenticated, fresh, provenance-bound, and cannot be supplied/overridden by an untrusted caller.
- [ ] Cross-tenant placement fails closed for missing/unknown/stale/unauthenticated mitigations and unsafe SMT policy.
- [ ] Production release evidence is machine-readable, tamper-evident, artifact-bound, retained, and independently verifiable.
- [ ] Owners, on-call escalation, runbooks, incident response, vulnerability SLAs, review cadence, exception ledger, compatibility matrix, and EOL policy are current.
- [ ] The final production gate records an explicit GO/NO-GO result with approver identity, timestamp, release digest, configuration/policy digests, and evidence bundle reference.

**Completion principle:** INV-43 should be considered production-ready only when the physical artifacts, executable controls, integration behavior, and retained evidence exist—not because a generic checklist runner reports the requirements as logically present.