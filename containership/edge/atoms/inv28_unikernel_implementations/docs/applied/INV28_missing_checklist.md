# INV-28 v4.2.0 — Missing Components Implementation & Verification Checklist

**Repository:** `inv28_unikernel_implementations`  
**Source audit:** `MISSING_COMPONENTS.md` in hardened v4.2.0 archive  
**Checklist scope:** all 100 post-hardening missing components / unresolved production gaps  
**Purpose:** convert every audit gap into concrete engineering work, tests, acceptance gates, and retained release evidence.

## How to use this checklist

- `[ ]` = not started; `[~]` = implemented but evidence/gate incomplete; `[x]` = complete and independently verifiable.
- **P0** items are integrity/safety/reproducibility blockers for a credible production release. **P1** items are production-readiness requirements. **P2** items deepen assurance, governance, and developer/operator maturity.
- A component is not complete merely because a file or field exists. Completion requires implementation **and** tests **and** release evidence **and** documentation/ownership where applicable.
- Production behavior must remain fail-closed: no silent downgrade, no implicit equivalence between toolchains, no unverified certification, and no same-name artifact substitution.
- Prefer immutable identities (version + digest + provenance) over mutable names/tags; prefer stable reason codes over human-only messages; retain historical state for auditability.

## Cross-cutting Definition of Done

- [ ] The implementation is represented in the relevant schema/model, not only prose.
- [ ] Input validation rejects malformed, ambiguous, stale, unsupported, or unauthenticated production data.
- [ ] Every decision is deterministic for the same request, registry revision, policy revision, certification snapshot, and clock value.
- [ ] No required workload/site constraint can be silently dropped or weakened.
- [ ] Security-sensitive state changes are authorized, versioned, auditable, and reversible where appropriate.
- [ ] Tests include success, refusal, boundary, tamper/fault, and migration/compatibility cases as applicable.
- [ ] CI blocks merge/release when mandatory tests, schemas, scans, or evidence are missing.
- [ ] Release evidence identifies the exact source, build, dependency lock, schemas, catalog, policy, tests, and produced artifact digests.
- [ ] Operational documentation includes owner, escalation path, rollback/disable behavior, and residual-risk handling.

## Recommended closure sequence

1. Establish reproducible packaging and real `pk_core` execution (items 2–5, 81–85, 89).
2. Make the toolchain/register/request/result/policy models production-complete and immutable (items 6, 9–30, 94–100).
3. Bind GAP-15 certification and artifact identity through INV-27 to close substitution and compatibility risks (items 13–15, 21, 41–45, 97–99).
4. Implement security/provenance controls and production evidence (items 31–38, 48, 52, 55, 76).
5. Add persistence, lifecycle, rollout/rollback/emergency controls, and resilience testing (items 27–30, 47, 51, 67–80).
6. Complete observability/explainability and broad assurance/maintenance tooling (items 49–66, 86–93).

## A. Declared-but-absent repository artifacts

### MC-001 — `MASTER.md`

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** README lineage says the 100 per-item master prompt/workflow documents exist, but the file is absent.  
**Target state:** Add the missing repository artifact/control **`MASTER.md`** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create `MASTER.md` at repository root and define its normative/non-normative status relative to `CHECKLIST.json` and `contract.py`.
- [ ] Provide exactly 100 indexed prompt/workflow entries, one per checklist requirement, with stable IDs matching `INV-28-C001`…`INV-28-C100`.
- [ ] For each entry include objective, preconditions, inputs, implementation steps, verification, evidence path, and refusal/NO_GO conditions.
- [ ] Add an automated consistency check that rejects duplicate/missing checklist IDs and detects drift between `MASTER.md` and `CHECKLIST.json`.
- [ ] Update README lineage text and changelog with the authoritative source and generation/editing policy.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-002 — `pk_core` dependency/package

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** required by `component.py`, `contract.py`, and the conformance tests, but not supplied.  
**Target state:** Add the missing repository artifact/control **`pk_core` dependency/package** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Vendor, package, or declare an installable `pk_core` dependency with an immutable version range/pin compatible with INV-28.
- [ ] Document the supported `pk_core` API surface used by `contract.py`, `component.py`, and tests (`Contract`, `Dependency`, `Slo`, `ChecklistItem`, `Finding`, `Component`).
- [ ] Add import-time compatibility validation that fails with an actionable message when `pk_core` is absent or incompatible.
- [ ] Ensure offline/air-gapped installation is possible via a wheelhouse or documented vendoring path if production requires it.
- [ ] Run the real `pk_core run`, `gate`, and `verify` commands in CI rather than import stubs and retain outputs.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path

---

### MC-003 — Dependency/install manifest

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no `pyproject.toml`, `requirements.txt`, `setup.cfg`, `setup.py`, lockfile, or equivalent describes how to obtain `pk_core` or install this package.  
**Target state:** Add the missing repository artifact/control **Dependency/install manifest** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add `pyproject.toml` using a modern build backend and declare package metadata, Python compatibility, and runtime/test/dev dependencies.
- [ ] Pin or constrain `pk_core` and all tooling dependencies; define optional dependency groups for test, lint, security, and release tasks.
- [ ] Generate and commit an appropriate lockfile or hash-pinned requirements export for reproducibility.
- [ ] Define editable-development and wheel/sdist installation paths and test both from a clean environment.
- [ ] Add deterministic bootstrap commands to README and CI; prohibit undeclared ambient dependencies.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path

---

### MC-004 — Machine-readable interface schema for `PK_TOOLCHAIN/1`

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** interface is named in the contract but no JSON Schema, WIT, protobuf, OpenAPI, or equivalent schema is present.  
**Target state:** Add the missing repository artifact/control **Machine-readable interface schema for `PK_TOOLCHAIN/1`** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Choose the canonical wire format for `PK_TOOLCHAIN/1` (JSON Schema is appropriate for the current Python/local model unless WIT/RPC is required upstream).
- [ ] Specify required fields, types, normalization rules, enums, min/max lengths, set/list uniqueness, semantic version format, timestamps, lifecycle, security metadata, capabilities, integrity identity, and extension rules.
- [ ] Assign a schema `$id`/version and define forward/backward compatibility expectations for `/1`.
- [ ] Generate positive and negative fixtures covering valid records, unknown fields, malformed tokens, empty sets, duplicates, stale review data, and unsupported enum values.
- [ ] Validate every persisted/imported register entry against the schema before constructing `Toolchain`.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] versioned interface/schema artifacts

---

### MC-005 — Machine-readable interface schema for `PK_TOOLCHAIN_SELECTION/1`

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** same gap for selection output.  
**Target state:** Add the missing repository artifact/control **Machine-readable interface schema for `PK_TOOLCHAIN_SELECTION/1`** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define `PK_TOOLCHAIN_SELECTION/1` as a schema-bound result envelope with request identity, selected toolchain identity/version/digest, policy version, decision timestamp, reason codes, eliminated candidates, certification references, and decision ID.
- [ ] Define a companion structured refusal payload rather than overloading successful selection output.
- [ ] Specify cardinality and truncation rules for `eliminated` diagnostics so responses are bounded.
- [ ] Make serialization deterministic/canonical where it participates in hashing or signing.
- [ ] Add round-trip and compatibility tests between Python result objects and the interface schema.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] versioned interface/schema artifacts

---

### MC-006 — Example register data / supported-toolchain catalog

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no persisted MirageOS/Unikraft/OSv/etc. registry dataset exists; examples live only inside assessment code.  
**Target state:** Add the missing repository artifact/control **Example register data / supported-toolchain catalog** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create a version-controlled `catalog/` or `registry/` data source containing supported MirageOS, Unikraft, OSv, Nanos, and any other approved implementations.
- [ ] Record explicit upstream versions/releases rather than generic product names and include source URLs/identifiers, supported architectures, runtimes, devices, maturity, lifecycle, security posture, review provenance, limitations, and integrity pins.
- [ ] Separate demonstration fixtures from production-approved catalog entries to prevent test data from becoming selectable.
- [ ] Add a loader that validates schema, verifies signatures/digests, rejects duplicates, and constructs the in-memory register deterministically.
- [ ] Define catalog ownership, review cadence, change-control, and release process; every catalog change must produce evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-007 — License file

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no `LICENSE` or equivalent licensing artifact is present.  
**Target state:** Add the missing repository artifact/control **License file** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Select the repository license and add the complete canonical `LICENSE` text; do not infer a license from neighboring repositories.
- [ ] Add SPDX license identifiers to `pyproject.toml` and source headers only if the chosen license/process requires them.
- [ ] Inventory third-party notices and ensure upstream toolchain names/data are used consistently with their licenses/trademarks.
- [ ] Add a CI check that fails when package metadata and `LICENSE` disagree.
- [ ] Document whether generated evidence/catalog data is covered by the same license.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-008 — Contribution/security policy

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no `SECURITY.md`, vulnerability-reporting instructions, or maintainer escalation metadata.  
**Target state:** Add the missing repository artifact/control **Contribution/security policy** as a version-controlled, reviewable part of the release.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add `SECURITY.md` with supported versions, private reporting channel, expected acknowledgement/remediation windows, disclosure policy, and escalation path.
- [ ] Add `CONTRIBUTING.md` defining review requirements for registry, schema, policy, and security-sensitive changes.
- [ ] Define CODEOWNERS/maintainer ownership for contract, policy, registry, schemas, and release evidence.
- [ ] Specify prohibited contributions (secrets, unverifiable catalog claims, unsigned production records) and evidence requirements.
- [ ] Link the policy from README and package metadata.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

## B. Toolchain model and selection capability gaps

### MC-009 — Toolchain version field

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** entries cannot distinguish supported upstream versions/releases.  
**Target state:** Extend the INV-28 domain and selection model so **Toolchain version field** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add immutable `version` (prefer parsed SemVer plus original upstream release identifier) to `Toolchain` and `PK_TOOLCHAIN/1`.
- [ ] Define whether the key is `(name, version)` rather than name alone, and update duplicate detection accordingly.
- [ ] Reject floating labels such as `latest` for production-selectable records unless resolved to an immutable version before registration.
- [ ] Include version in selection output, decision logs, compatibility matrices, and downstream build binding.
- [ ] Test ordering/equality semantics independently from maturity selection so version does not accidentally become an implicit preference.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-010 — Runtime/profile field

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** contract ownership includes language/runtime support, but the model stores only language and architecture.  
**Target state:** Extend the INV-28 domain and selection model so **Runtime/profile field** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Model runtime/profile as explicit structured metadata (for example language runtime, ABI/profile, standard library/runtime version, execution profile).
- [ ] Allow a toolchain version to advertise multiple certified profiles without conflating them with language names.
- [ ] Extend selection requirements to request profile constraints and fail closed when no certified profile matches.
- [ ] Normalize profile identifiers and version ranges with documented syntax; reject ambiguous free text in production records.
- [ ] Cross-link each selectable profile to GAP-15 certification evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-011 — Device-support model

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** the repository description explicitly says implementations differ by device set, but `Toolchain` has no device capability field.  
**Target state:** Extend the INV-28 domain and selection model so **Device-support model** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define a device capability taxonomy covering the devices/interfaces relevant to unikernel execution (network, block, console, clock/timer, entropy, vsock, virtio classes, platform-specific devices).
- [ ] Represent required, optional, unsupported, and emulated device capabilities per toolchain/profile/version.
- [ ] Extend workload/site requirements so required devices are explicit and selection rejects incomplete matches.
- [ ] Keep device identifiers stable and machine-readable; put explanatory notes in separate fields.
- [ ] Build compatibility fixtures/tests for each supported VMM/device combination and record evidence references.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-012 — Feature/capability model

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** selection can only match language and architecture; it cannot enforce workload feature requirements.  
**Target state:** Extend the INV-28 domain and selection model so **Feature/capability model** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create a namespaced capability model for workload-visible requirements such as TLS/networking features, filesystem semantics, threading/SMP, clocks, entropy, storage, observability hooks, and runtime features.
- [ ] Differentiate boolean capabilities from parameterized capabilities/versions and define comparison semantics.
- [ ] Extend `SelectionRequest` to carry required and optional capabilities and constraints.
- [ ] Make `select()` evaluate every required capability with stable elimination codes; prohibit silent downgrade.
- [ ] Add property tests proving a selected toolchain is always a superset of mandatory workload capabilities.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-013 — Hypervisor/VMM compatibility metadata

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no supported VMM/hypervisor matrix per implementation.  
**Target state:** Extend the INV-28 domain and selection model so **Hypervisor/VMM compatibility metadata** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create explicit hypervisor/VMM compatibility records keyed by toolchain version/profile, VMM name/version, machine type, architecture, and boot mode.
- [ ] Capture status such as certified/supported/experimental/unsupported plus evidence IDs and last-tested timestamp.
- [ ] Require selection/build planning to intersect toolchain support with site VMM capabilities.
- [ ] Reject stale/unverified compatibility rows in production according to policy.
- [ ] Exercise the matrix in integration tests against the actual INV-27 execution adapter(s).
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-014 — Provider/platform compatibility metadata

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no cloud/edge/bare-metal provider support matrix.  
**Target state:** Extend the INV-28 domain and selection model so **Provider/platform compatibility metadata** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define provider/platform targets (cloud provider, edge appliance, bare metal, region/site class, instance/machine family where relevant) as structured identifiers.
- [ ] Separate vendor support claims from locally certified support and retain provenance for each claim.
- [ ] Add site/provider context to selection requests or pre-filtered certified capability input.
- [ ] Prevent a generic architecture match from implying provider support.
- [ ] Add at least one negative test where architecture matches but provider/platform certification does not.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-015 — Protocol/ABI compatibility metadata

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no ABI, WIT/component-model, network-stack, filesystem, or API compatibility information.  
**Target state:** Extend the INV-28 domain and selection model so **Protocol/ABI compatibility metadata** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Model ABI/API/protocol compatibility as versioned structured capabilities: application ABI, WIT/component model if applicable, network stack features, filesystem interfaces, boot protocol, management API, and image format.
- [ ] Define exact compatibility operators (exact, range, minimum, feature-set) rather than string equality where versions are involved.
- [ ] Bind compatibility declarations to toolchain version/profile and certification evidence.
- [ ] Feed required protocol/ABI constraints into selection and refusal diagnostics.
- [ ] Add fixtures for incompatible major versions, unsupported optional features, and ambiguous version ranges.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-016 — Security-response metadata beyond a boolean

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** `security_contact` records existence only; there is no contact identity/reference, response SLA, advisory feed, or disclosure policy.  
**Target state:** Extend the INV-28 domain and selection model so **Security-response metadata beyond a boolean** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Replace `security_contact: bool` with a structured security posture containing contact reference, supported disclosure channel, advisory feed, response SLA, maintenance status, and provenance.
- [ ] Keep sensitive contact details outside public logs; store references/aliases when appropriate.
- [ ] Define minimum production posture in policy rather than hard-coding a boolean test.
- [ ] Track upstream and internal security ownership separately if both matter.
- [ ] Test missing/expired/unverified contact metadata and policy changes.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls

---

### MC-017 — Security-review provenance

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** `reviewed_at` is a logical integer only; no reviewer, evidence URI/hash, review result, or real timestamp is recorded.  
**Target state:** Extend the INV-28 domain and selection model so **Security-review provenance** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Replace/augment `reviewed_at` with an immutable review record containing UTC timestamp, reviewer identity/role, decision, scope, evidence URI/object ID, evidence digest, and review method/version.
- [ ] Define cryptographic or repository identity for the reviewer/evidence producer when production assurance requires it.
- [ ] Make review result explicit (approved/conditional/rejected) and prevent rejected/unverified records from selection.
- [ ] Validate timestamp ordering and prohibit future timestamps beyond a small clock-skew policy.
- [ ] Carry review provenance into selection evidence and decision logs.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls

---

### MC-018 — Per-toolchain review interval

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** only one global `REVIEW_INTERVAL` exists; no implementation-specific cadence.  
**Target state:** Extend the INV-28 domain and selection model so **Per-toolchain review interval** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add `review_interval`/`review_expires_at` per toolchain/profile, with policy-controlled defaults and maximums.
- [ ] Allow higher-risk/less mature toolchains to require shorter intervals without changing global code.
- [ ] Define precedence among catalog value, policy maximum, and emergency override; use the strictest applicable bound.
- [ ] Calculate staleness from real review timestamps and test boundary conditions exactly at expiry.
- [ ] Expose upcoming-expiry metrics/alerts before a toolchain becomes unselectable.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls

---

### MC-019 — Known limitation semantics in selection

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** limitations are now representable but are not structured or evaluated against workload requirements.  
**Target state:** Extend the INV-28 domain and selection model so **Known limitation semantics in selection** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Replace free-text `limitations` with structured limitation records containing code, scope, severity, affected versions/profiles, machine-readable predicate, description, mitigation, and evidence.
- [ ] Allow a workload/site constraint to conflict with a limitation and eliminate the candidate deterministically.
- [ ] Distinguish advisory limitations from hard incompatibilities and define policy treatment for each.
- [ ] Include limitation reason codes in selection/refusal results without leaking unsafe internal detail.
- [ ] Test conflicts such as unsupported SMP/device/network behavior and verify no silent selection occurs.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-020 — Explicit deprecation/EOL status

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no lifecycle state prevents selection of deprecated or end-of-life implementations.  
**Target state:** Extend the INV-28 domain and selection model so **Explicit deprecation/EOL status** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add lifecycle enum/state such as active, deprecated, security-only, quarantined, EOL, revoked, with effective dates and reason metadata.
- [ ] Define which states are selectable per environment; production should fail closed for prohibited states.
- [ ] Support scheduled deprecation/EOL transitions and advance warnings.
- [ ] Tie EOL to vulnerability response and support SLA metadata.
- [ ] Add tests for historical/transition boundaries and emergency revocation.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls

---

### MC-021 — Toolchain integrity identity

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no digest, signed release identity, provenance/SBOM reference, or immutable version pin exists to prevent substitution between selection and build.  
**Target state:** Extend the INV-28 domain and selection model so **Toolchain integrity identity** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add immutable toolchain identity fields: upstream source/release, artifact digest(s), signing identity, provenance/SBOM references, and optional source commit/tree digest.
- [ ] Use content digests with explicit algorithms and canonical encoding; reject malformed/weak/unknown algorithms by policy.
- [ ] Include identity in the selection result and require INV-27/build stages to consume and verify the same identity.
- [ ] Design identity for multi-artifact toolchains/profile bundles without collapsing distinct artifacts.
- [ ] Test substitution attempts where name/version match but digest/signature differs.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] security/evidence/provenance controls

---

### MC-022 — Policy-driven selection rules

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** production logic is hard-coded; there is no injected policy set, environment policy version, waiver model, or tenant/site policy evaluation.  
**Target state:** Extend the INV-28 domain and selection model so **Policy-driven selection rules** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Extract selection policy from `ToolchainRegister.select()` into a versioned policy object/engine with explicit inputs and deterministic evaluation.
- [ ] Represent environment, site, tenant/global rules, maturity, lifecycle, review freshness, security posture, waiver policy, and certification requirements declaratively where practical.
- [ ] Record exact policy version/digest with every decision.
- [ ] Define conflict resolution and precedence rules and make deny rules fail closed.
- [ ] Add golden tests showing identical inputs + policy produce identical decision/reason codes.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-023 — Selection request schema/object

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** selection accepts loose keyword strings rather than a validated workload-requirements object.  
**Target state:** Extend the INV-28 domain and selection model so **Selection request schema/object** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Introduce immutable `SelectionRequest` with schema version, request/operation ID, workload requirements, language/runtime/profile, architecture, capabilities/devices, environment, site context, policy reference, and decision time.
- [ ] Validate lengths, enums, identifiers, sets, timestamps, and mutually exclusive fields at construction/schema boundary.
- [ ] Normalize once at ingestion and preserve raw input only in protected diagnostics if needed.
- [ ] Add explicit optional-vs-required constraints and defaulting rules; prohibit implicit production defaults that weaken safety.
- [ ] Refactor `select()` to accept the request object while preserving a temporary compatibility adapter if needed.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts

---

### MC-024 — Selection result type

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** returns an untyped dictionary rather than a validated immutable result object/schema-bound record.  
**Target state:** Extend the INV-28 domain and selection model so **Selection result type** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Introduce immutable `SelectionResult` instead of a raw dict, with a serializer bound to `PK_TOOLCHAIN_SELECTION/1`.
- [ ] Include selected record identity, version/profile/digest, request ID, decision ID, policy/version, certification refs, normalized requirements, stable reason codes, eliminated-summary, timestamp, and evidence linkage.
- [ ] Prevent callers from mutating the object after decision.
- [ ] Define canonical serialization and equality semantics for audit/replay.
- [ ] Test schema round-trips and downstream consumption by INV-27/build integration.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts

---

### MC-025 — Stable reason codes

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** elimination/refusal reasons are human strings only; no machine-readable reason enum/code.  
**Target state:** Extend the INV-28 domain and selection model so **Stable reason codes** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define an enum/catalog of stable decision reason codes for mismatch classes: language, architecture, runtime/profile, capability, device, provider, VMM, ABI/protocol, maturity, lifecycle, security posture, stale review, certification, policy, integrity, resource bound, and internal error.
- [ ] Assign codes independent of human message wording and document stability guarantees.
- [ ] Allow one candidate to accumulate multiple bounded reason codes when useful, with deterministic ordering.
- [ ] Map codes to metrics/alerts and operator explanations.
- [ ] Add tests asserting codes rather than fragile prose strings.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts

---

### MC-026 — Explicit refusal object

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** failure is an exception with interpolated text; no structured refusal record listing unmet constraints.  
**Target state:** Extend the INV-28 domain and selection model so **Explicit refusal object** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create immutable `SelectionRefusal`/error envelope carrying request ID, refusal code, unmet constraints, bounded eliminated candidate summaries, policy version, timestamp, and correlation ID.
- [ ] Differentiate expected no-match/policy refusal from validation errors, dependency failures, and internal defects.
- [ ] Ensure refusal serialization is safe for callers and does not leak secrets or tenant-isolated data.
- [ ] Provide conversion to exceptions only at the Python API boundary if exception ergonomics are desired.
- [ ] Test zero-candidate, all-policy-denied, stale-certification, and integrity-failure refusals.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts

---

### MC-027 — Register update/remove lifecycle

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** register supports add only; there is no controlled update, retire, remove, or replace operation.  
**Target state:** Extend the INV-28 domain and selection model so **Register update/remove lifecycle** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define administrative lifecycle operations: create/register, update metadata, replace immutable version, deprecate, quarantine/disable, retire, and delete/tombstone.
- [ ] Require optimistic version/ETag or expected revision on mutations to prevent lost updates.
- [ ] Validate state transitions with an explicit state machine; disallow unsafe resurrection without approval.
- [ ] Record actor, reason, before/after digest, approval, timestamp, and change ticket/evidence for every mutation.
- [ ] Make destructive removal rare; prefer immutable historical records plus inactive states for auditability.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] persistent state / lifecycle / recovery design

---

### MC-028 — Registry persistence

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** entries are in-memory only; no durable source of truth or serialization/deserialization path.  
**Target state:** Extend the INV-28 domain and selection model so **Registry persistence** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Choose a durable registry source of truth (version-controlled signed catalog, database, or equivalent) consistent with deployment topology.
- [ ] Define canonical serialization, schema version, migrations, atomic writes, backup/restore, and startup loading behavior.
- [ ] Do not mutate production state only in memory; define write-through/commit semantics for administrative changes.
- [ ] Verify data before activation and keep last-known-good snapshot for recovery.
- [ ] Add restart tests proving registry contents and revisions survive process restarts exactly.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] persistent state / lifecycle / recovery design

---

### MC-029 — Registry concurrency control

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no locking/versioning/CAS semantics for concurrent updates.  
**Target state:** Extend the INV-28 domain and selection model so **Registry concurrency control** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define registry revision/epoch semantics and use locking, transactional updates, or compare-and-swap appropriate to the persistence backend.
- [ ] Make reads consistent enough that one selection observes one coherent registry revision.
- [ ] Detect write/write conflicts and return explicit conflict errors instead of last-writer-wins corruption.
- [ ] Test concurrent register/update/quarantine operations and selection during mutation.
- [ ] Include registry revision in decision evidence for deterministic replay.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] persistent state / lifecycle / recovery design

---

### MC-030 — Registry authenticity/integrity verification

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no signature/hash verification for loaded registry data.  
**Target state:** Extend the INV-28 domain and selection model so **Registry authenticity/integrity verification** is explicit, validated, machine-readable, and enforced rather than implied.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Sign or hash canonical registry/catalog artifacts and verify integrity/authenticity before loading or activating them.
- [ ] Define trust roots/key rotation/revocation and supported algorithms; keep key material outside the repository.
- [ ] Fail closed on signature mismatch, unknown signer, rollback to disallowed revision, malformed canonicalization, or hash mismatch.
- [ ] Record verified artifact digest/signing identity in runtime status and decision evidence.
- [ ] Add tampering, replay, rollback, and key-rotation tests.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls
- [ ] persistent state / lifecycle / recovery design

---

## C. Security and supply-chain gaps

### MC-031 — Threat-model artifact

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** threats are short contract strings; no dedicated threat model with assets, actors, trust boundaries, mitigations, and test mappings.  
**Target state:** Implement **Threat-model artifact** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create `THREAT_MODEL.md` (or machine-readable equivalent plus narrative) using explicit assets, actors, entry points, trust boundaries, abuse cases, assumptions, and mitigations.
- [ ] Cover the contract threats plus registry poisoning, stale certification, policy tampering, downgrade, toolchain substitution, malicious catalog metadata, dependency compromise, log/evidence tampering, DoS, and cross-tenant/site leakage.
- [ ] Map each threat to preventive/detective controls, owner, residual risk, and one or more security tests.
- [ ] Include data-flow/trust-boundary diagrams and identify where signatures/digests are verified.
- [ ] Require threat-model review for interface, trust-boundary, persistence, or policy changes.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-032 — SBOM

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no SPDX/CycloneDX or equivalent software bill of materials.  
**Target state:** Implement **SBOM** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Generate an SPDX or CycloneDX SBOM for the Python package, `pk_core`, build tooling included in release artifacts, and any vendored/runtime dependencies.
- [ ] Include exact versions, package URLs/identifiers, hashes where available, licenses, and dependency relationships.
- [ ] Generate SBOM from the locked build environment rather than hand-maintained prose.
- [ ] Attach SBOM digest to release provenance and selection/catalog artifacts where relevant.
- [ ] Validate SBOM schema and archive it with every released version.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-033 — Dependency vulnerability scan configuration/evidence

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no scanner configuration or results.  
**Target state:** Implement **Dependency vulnerability scan configuration/evidence** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Select an approved dependency vulnerability scanner and commit minimal policy/configuration including severity thresholds, ignored advisory format, and expiry requirements.
- [ ] Scan both locked dependencies and produced SBOM; cover transitive dependencies.
- [ ] Fail CI/release on policy-violating known vulnerabilities unless an approved unexpired waiver exists.
- [ ] Record scanner/version/database timestamp and raw machine-readable results as evidence.
- [ ] Add recurring scheduled scans so newly disclosed CVEs are detected without source changes.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-034 — Static-analysis configuration/evidence

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no Ruff/Pylint/Bandit/Semgrep/mypy configuration or recorded run.  
**Target state:** Implement **Static-analysis configuration/evidence** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Configure formatting/lint/type/security static analysis with pinned versions and repository-local configuration.
- [ ] At minimum cover correctness/style, type checking, and security patterns relevant to Python; add Semgrep/custom rules for INV-28 invariants if justified.
- [ ] Treat production-path findings with explicit severity policy; avoid blanket excludes.
- [ ] Run tools in CI and persist machine-readable reports or normalized gate evidence.
- [ ] Seed tests with known-bad fixtures/rules to verify the analyzers actually fail when expected.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-035 — Secret scanning configuration/evidence

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no secret-scanning policy or result.  
**Target state:** Implement **Secret scanning configuration/evidence** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Configure secret scanning for repository history/change sets and release artifacts with an approved baseline mechanism.
- [ ] Cover API keys, private keys, tokens, credentials, connection strings, and high-entropy secrets; exclude only reviewed false positives.
- [ ] Run on pull requests and full history where feasible, and define revocation response if a real secret is found.
- [ ] Keep security contact references from item 16 non-secret by design.
- [ ] Retain scan evidence without exposing the secret value itself.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-036 — Artifact signing/provenance

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no signing, SLSA provenance, attestations, checksums, or release verification workflow.  
**Target state:** Implement **Artifact signing/provenance** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define release signing and provenance generation for source archives/wheels/catalog/evidence artifacts.
- [ ] Use immutable checksums plus a signing/attestation mechanism and record builder identity, source revision, dependency lock digest, and build parameters.
- [ ] Target an explicit SLSA/provenance level appropriate to the environment and document gaps if full hermeticity is not yet available.
- [ ] Verify signatures/provenance during install/deploy and before activating catalog updates.
- [ ] Publish a machine-readable manifest linking every release artifact to digest, SBOM, tests, gate result, and provenance.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-037 — CVE/advisory ingestion

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** optional automated upstream CVE tracking is not implemented.  
**Target state:** Implement **CVE/advisory ingestion** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Implement upstream advisory ingestion for each supported toolchain/version using authoritative feeds where available and a documented fallback process where not.
- [ ] Normalize advisories to affected version/profile, severity, publication/update time, fix availability, and source reference.
- [ ] Re-evaluate production selectability when an advisory changes security posture or invalidates certification.
- [ ] Deduplicate feed entries and protect against feed outages/poisoning with source authentication and last-known-good handling.
- [ ] Emit metrics/alerts for newly affected active toolchains and overdue remediation.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-038 — Security exception/waiver mechanism

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no structured exception with owner, scope, approval, and expiry.  
**Target state:** Implement **Security exception/waiver mechanism** as a verifiable security/supply-chain control with retained machine-readable evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define a signed/approved waiver record with unique ID, exact control/reason code, affected toolchain/version/profile/site/environment, business/technical justification, owner, approver, issue date, expiry, and compensating controls.
- [ ] Policy must distinguish waivable from non-waivable controls; integrity substitution and mandatory production safety gates should default non-waivable unless governance explicitly says otherwise.
- [ ] Apply waivers only by exact scope and record waiver ID in selection evidence.
- [ ] Automatically expire waivers and alert before expiry; prohibit silent renewal.
- [ ] Test wrong-scope, expired, revoked, and tampered waivers.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

## D. Tests and certification gaps

### MC-039 — Self-contained unit tests for `Toolchain` validation

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** the shipped test file primarily checks inherited `pk_core` conformance and does not directly cover all domain validation cases.  
**Target state:** Add executable verification for **Self-contained unit tests for `Toolchain` validation** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Expand `tests/test_toolchain_domain.py` into a self-contained domain suite that imports the real package without `pk_core` stubs for the pure domain layer where practical.
- [ ] Test every `Toolchain.__post_init__` validation path: name, maturity, security fields, review time, languages, architectures, limitations, normalization, immutability, and future added fields.
- [ ] Test `ToolchainRegister.register`, duplicate keys, snapshots, staleness boundaries, deterministic selection, and every rejection gate.
- [ ] Use table-driven cases for Unicode/case/whitespace normalization and pathological but valid input sizes within bounds.
- [ ] Separate domain tests from `pk_core` conformance tests so local correctness can be proven even if the external framework is unavailable.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] `pk_core` packaging/conformance path

---

### MC-040 — Public-interface contract tests

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no schema/interface tests for register/select payload compatibility.  
**Target state:** Add executable verification for **Public-interface contract tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create schema conformance tests for `PK_TOOLCHAIN/1` and `PK_TOOLCHAIN_SELECTION/1` plus refusal/request schemas introduced by this plan.
- [ ] Maintain canonical golden fixtures and deliberately invalid fixtures for each required field and enum/constraint.
- [ ] Test compatibility policy across schema minor revisions and assert breaking changes require a new major interface version.
- [ ] Round-trip Python objects through canonical serialization and schema validation.
- [ ] Add consumer-driven contract tests with INV-27/GAP-15 adapters where those repositories/interfaces are available.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] versioned interface/schema artifacts

---

### MC-041 — Integration tests with `INV-27 Unikernel execution`

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** declared downstream dependency is not exercised.  
**Target state:** Add executable verification for **Integration tests with `INV-27 Unikernel execution`** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define an INV-27 test adapter/fixture that consumes `SelectionResult` and verifies the selected version/profile/digest before execution.
- [ ] Exercise successful handoff, missing artifact, digest mismatch, unsupported VMM/device, revoked selection, and stale registry revision.
- [ ] Assert INV-27 never substitutes a same-name different artifact/version.
- [ ] Propagate decision/correlation IDs across the boundary and verify audit linkage.
- [ ] Run the integration in CI against pinned compatible INV-27 versions and capture machine-readable evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-042 — Integration tests with `GAP-15 Runtime compatibility certification`

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** declared upstream dependency is not exercised.  
**Target state:** Add executable verification for **Integration tests with `GAP-15 Runtime compatibility certification`** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define the GAP-15 certification interface and import real certified toolchain/profile/version/platform tuples with evidence identity and expiry.
- [ ] Make production selection depend on valid certification rather than local self-asserted compatibility fields.
- [ ] Test certified, uncertified, expired, revoked, mismatched-digest, and partial-capability cases.
- [ ] Verify schema/version negotiation and fail closed on unknown GAP-15 interface versions.
- [ ] Record exact certification object/digest in the selection result and decision ledger.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-043 — Integration tests with `GAP-08 OTA lifecycle/rollback`

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** optional peer dependency is not exercised.  
**Target state:** Add executable verification for **Integration tests with `GAP-08 OTA lifecycle/rollback`** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define the optional GAP-08 integration contract for staged toolchain-version rollout and rollback state.
- [ ] Exercise catalog activation after rollout approval, rollback to prior signed revision, partial rollout failure, and emergency halt.
- [ ] Ensure optional dependency absence is explicit and does not masquerade as successful rollback capability.
- [ ] Propagate release/catalog revision and evidence head across the integration.
- [ ] Document when GAP-08 is required by environment policy even though the contract marks it optional globally.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-044 — Cross-architecture compatibility tests

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no executable x86_64/aarch64 compatibility matrix.  
**Target state:** Add executable verification for **Cross-architecture compatibility tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Build an executable architecture matrix for every supported toolchain version/profile across `x86_64`, `aarch64`, and any future architecture explicitly advertised.
- [ ] Use real boot/execution smoke tests where feasible; do not certify from metadata alone.
- [ ] Include architecture-specific device/VMM combinations and artifact digests.
- [ ] Record test host/emulator details and distinguish emulated from native evidence.
- [ ] Automatically remove/deny architecture claims whose certification is missing or expired.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-045 — Cross-toolchain/version compatibility tests

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no matrix for MirageOS/Unikraft/OSv/Nanos versions.  
**Target state:** Add executable verification for **Cross-toolchain/version compatibility tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create a matrix spanning supported releases of MirageOS, Unikraft, OSv, Nanos, and future catalog entries, including profile/runtime and adjacent interface versions.
- [ ] Define minimum/maximum supported versions and explicit unsupported combinations rather than assuming latest.
- [ ] Run a representative compatibility suite per matrix row and retain result/evidence IDs.
- [ ] Test upgrade and downgrade edges, including schema migrations and artifact identity changes.
- [ ] Drive published compatibility data from verified results rather than hand-edited marketing claims.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-046 — Fuzz/property tests

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no fuzzing or property-based testing for register inputs and selection constraints.  
**Target state:** Add executable verification for **Fuzz/property tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Use property-based testing for `Toolchain`, `SelectionRequest`, policy evaluation, registry lifecycle, and serialization invariants.
- [ ] Generate invalid/edge tokens, large capability sets within configured limits, duplicate-normalized names, timestamp boundaries, lifecycle transitions, and conflicting requirements.
- [ ] Add fuzz targets for schema/parsers/loaders and any future WIT/RPC/HTTP input boundary.
- [ ] Persist minimized regression cases from discovered failures.
- [ ] Define time/iteration budgets for CI and a deeper scheduled fuzz job with crash artifact retention.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-047 — Concurrency/race tests

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Add executable verification for **Concurrency/race tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Identify shared mutable state in the persistence/cache/registry implementation and define a concurrency model before adding threads/processes/distributed writers.
- [ ] Create deterministic race tests for concurrent register/update/quarantine, revision conflicts, reads during writes, cache invalidation, and audit-log append.
- [ ] Use barriers/fault injection rather than relying only on probabilistic stress.
- [ ] Assert no lost updates, torn reads, duplicate active keys, or decisions spanning inconsistent registry revisions.
- [ ] Run stress/race tests repeatedly in CI/scheduled jobs and archive seeds on failure.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] persistent state / lifecycle / recovery design

---

### MC-048 — Threat-derived security tests

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent as a dedicated suite.  
**Target state:** Add executable verification for **Threat-derived security tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Derive one or more executable tests from every threat-model entry and give each threat/test a stable ID.
- [ ] Include registry tampering, signature failure, rollback/replay, stale review/certification, downgrade, policy bypass, malicious limitation strings, oversized input DoS, cross-site leakage, and build substitution.
- [ ] Verify fail-closed behavior and stable refusal codes for expected attacks.
- [ ] Test security logging contains sufficient forensic identifiers but redacts secrets/sensitive fields.
- [ ] Require threat-to-test traceability before the production gate can pass.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-049 — Benchmark suite

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no startup, selection latency, registry scale, memory, throughput, or tail-latency benchmarks.  
**Target state:** Add executable verification for **Benchmark suite** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create a benchmark harness measuring cold import/start, catalog load/verification, selection p50/p95/p99, refusal latency, registry mutation latency, memory footprint, and throughput under realistic registry sizes.
- [ ] Define deterministic datasets and publish hardware/runtime/environment metadata with results.
- [ ] Establish performance budgets and regression thresholds rather than recording numbers without a gate.
- [ ] Measure worst-case candidate elimination and large bounded diagnostic generation.
- [ ] Store benchmark outputs as versioned machine-readable evidence and compare releases.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-050 — Soak/burst/fleet-scale tests

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Add executable verification for **Soak/burst/fleet-scale tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create sustained-load soak tests long enough to expose leaks/state growth and burst tests that exceed expected peak selection/mutation rates.
- [ ] Model fleet-scale registry sizes, site counts, capability cardinality, and concurrent selection requests.
- [ ] Observe memory, CPU, latency tails, log volume, audit-ledger growth, and cache behavior.
- [ ] Inject catalog refreshes/security revocations during load and verify safety properties remain intact.
- [ ] Define pass/fail saturation and recovery criteria and retain trend evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-051 — Disaster/partition/reconnect/degraded-control-plane tests

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent/not modeled.  
**Target state:** Add executable verification for **Disaster/partition/reconnect/degraded-control-plane tests** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Model which external dependencies can partition or degrade (registry store, GAP-15, policy store, signing/verification service, telemetry backend, GAP-08).
- [ ] Define safe behavior for each dependency outage: fail closed, use bounded last-known-good, read-only mode, or explicit degraded mode.
- [ ] Test partition, stale cache, reconnect, duplicate delivery, reordered updates, and dependency timeouts.
- [ ] Verify recovery does not resurrect revoked toolchains or lose registry revisions/audit records.
- [ ] Emit distinct degraded-control-plane status and alerts rather than generic internal errors.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] persistent state / lifecycle / recovery design

---

### MC-052 — Machine-readable production acceptance evidence

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no generated certification artifact is included.  
**Target state:** Add executable verification for **Machine-readable production acceptance evidence** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define a signed/versioned production acceptance record containing component version, source revision, build/provenance digest, dependency lock digest, schema versions, catalog digest, policy digest, test/gate results, security scan summaries, benchmark results, compatibility matrix reference, and approver/owner.
- [ ] Use machine-readable JSON (or equivalent) with a schema and canonical digest.
- [ ] Generate it only from CI/release automation after all mandatory gates pass; never hand-edit production verdicts.
- [ ] Link acceptance evidence to `pk_core gate` output once dependency is available.
- [ ] Make deploy/activation logic verify the evidence belongs to the exact released artifact.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-053 — Coverage report/threshold

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no test coverage configuration or evidence.  
**Target state:** Add executable verification for **Coverage report/threshold** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Configure coverage collection for unit/contract/integration suites with branch coverage enabled for safety/refusal logic.
- [ ] Set explicit thresholds globally and for critical modules; avoid using a high aggregate number to hide untested decision branches.
- [ ] Publish HTML for humans and XML/JSON machine evidence for CI.
- [ ] Track exclusions with justification and review ownership.
- [ ] Add trend/regression checks and fail when critical branch coverage drops.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-054 — Mutation testing

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no evidence that refusal/safety branches resist test mutation.  
**Target state:** Add executable verification for **Mutation testing** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add mutation testing focused on `Toolchain` validation, staleness, production maturity/security gates, policy evaluation, digest/certification checks, and refusal paths.
- [ ] Choose a Python mutation tool compatible with the supported runtime and pin it.
- [ ] Set a mutation score threshold for critical modules and review surviving mutants individually.
- [ ] Run a targeted PR subset plus a deeper scheduled/release job if runtime is high.
- [ ] Retain survivor lists and add regression tests before accepting security-relevant equivalent/non-equivalent mutants.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-055 — `python -O` full-suite evidence in this archive

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** test exists, but cannot run without external `pk_core`.  
**Target state:** Add executable verification for **`python -O` full-suite evidence in this archive** and make its result part of release certification evidence.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Execute the complete real test/conformance suite under normal Python and `python -O` using the packaged `pk_core` dependency.
- [ ] Verify no safety check relies on `assert` side effects or optimizer-removed assertions.
- [ ] Compare gate/evidence results between optimized and non-optimized execution for semantic equivalence.
- [ ] Run from an installed wheel in a clean environment, not only the source tree.
- [ ] Archive command line, interpreter version, dependency lock, stdout/stderr digest, and gate artifacts with the release.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path
- [ ] security/evidence/provenance controls

---

## E. Observability and explainability gaps

### MC-056 — Runtime health/readiness endpoint or function

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Implement **Runtime health/readiness endpoint or function** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Expose a minimal health API/function reporting process alive status separately from readiness to serve selections.
- [ ] Readiness must validate loaded registry revision, schema/policy compatibility, signature verification, required dependency availability/freshness, and no fatal initialization error.
- [ ] Define degraded/read-only states distinctly and never report ready when production selection would necessarily fail for infrastructure reasons.
- [ ] Keep health checks bounded and side-effect free.
- [ ] Add unit/integration tests for startup, dependency loss, stale catalog/certification, and recovery transitions.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] observability / operations integration

---

### MC-057 — Version/config/dependency-status endpoint

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent beyond static package version metadata.  
**Target state:** Implement **Version/config/dependency-status endpoint** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Expose a status view containing component version, source/build identity, `pk_core` version, schema versions, policy digest/version, registry revision/digest, catalog load time, certification snapshot identity, and enabled feature flags.
- [ ] Do not expose secrets, private keys, raw security contact information, or tenant-sensitive data.
- [ ] Make output machine-readable and stable enough for automation plus a concise human rendering.
- [ ] Include compatibility/dependency status with explicit unknown/degraded states.
- [ ] Test status output against release manifest/provenance to detect drift.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] versioned interface/schema artifacts
- [ ] observability / operations integration

---

### MC-058 — Metrics emission

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** contract names signals, but no metrics implementation/exporter exists.  
**Target state:** Implement **Metrics emission** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Implement the contract signals `toolchains_registered`, `selections`, `selection_refusals`, and `stale_reviews` with documented names, units, labels, and cardinality budgets.
- [ ] Add latency, error, dependency, registry revision/load, certification freshness, cache, and saturation metrics required by operations.
- [ ] Keep high-cardinality identifiers such as workload/decision IDs out of metric labels.
- [ ] Define exporter abstraction/integration (e.g., OpenTelemetry metrics/Prometheus bridge) without making the core selection logic depend on backend availability.
- [ ] Test counter/gauge semantics and label bounds; telemetry failure must not change decision correctness.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] observability / operations integration

---

### MC-059 — Structured logging

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no logger, event schema, stable operation IDs, tenant/workload IDs, or redaction policy.  
**Target state:** Implement **Structured logging** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define a structured event schema for registration changes, policy evaluations, selections/refusals, dependency health, integrity failures, and administrative actions.
- [ ] Include timestamp, component/version, operation/decision ID, registry revision, policy version, site/workload identifiers where permitted, reason codes, and outcome.
- [ ] Implement a redaction/classification policy for security contacts, tenant/workload fields, paths, credentials, and raw payloads.
- [ ] Use stable event names/severity levels and bounded field sizes.
- [ ] Add tests for required fields, redaction, deterministic correlation, and logger failure isolation.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls
- [ ] observability / operations integration

---

### MC-060 — Trace propagation

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Implement **Trace propagation** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Adopt trace context propagation for external interfaces and adjacent integrations without forcing tracing into pure data-model code.
- [ ] Create spans for catalog load/verification, policy evaluation, selection, certification lookup, persistence mutation, and downstream handoff.
- [ ] Propagate W3C Trace Context or the platform standard and link decision IDs to traces.
- [ ] Apply sampling/privacy rules so traces do not leak high-cardinality sensitive payloads.
- [ ] Test context propagation across INV-27/GAP-15 adapters and behavior when tracing is disabled/unavailable.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] observability / operations integration

---

### MC-061 — Safe high-cardinality diagnostics

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Implement **Safe high-cardinality diagnostics** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define which high-cardinality diagnostic fields are permitted in logs/traces/audit stores versus metrics.
- [ ] Use opaque hashed/pseudonymous workload/site identifiers where full identifiers are unnecessary.
- [ ] Bound eliminated-candidate details and provide secure drill-down by decision ID rather than emitting entire catalogs.
- [ ] Add field-level classification/redaction and export controls.
- [ ] Test adversarial input strings for secret/PII leakage, log injection, truncation, and cardinality explosion.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] observability / operations integration

---

### MC-062 — Decision audit log

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** returned `reason`/`eliminated` values are ephemeral; no durable selection-decision ledger exists.  
**Target state:** Implement **Decision audit log** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Persist an append-only decision ledger containing request digest, normalized requirements, registry revision, policy version/digest, certification refs, selected identity or refusal, stable reason codes, timestamp, and correlation/trace IDs.
- [ ] Make ledger writes tamper-evident (hash chain/signature/immutable storage as appropriate) and define behavior if persistence fails.
- [ ] Separate confidential fields from broadly accessible operational metadata.
- [ ] Provide deterministic replay tooling that can explain a historical decision from the referenced snapshots.
- [ ] Define retention/indexing and tests for ordering, tamper detection, partial-write recovery, and audit export.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls
- [ ] persistent state / lifecycle / recovery design
- [ ] observability / operations integration

---

### MC-063 — Operator explain view

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no CLI/API/report tying selection to policy, input state, compatibility evidence, and constraints.  
**Target state:** Implement **Operator explain view** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Provide CLI/API `explain` functionality keyed by decision ID or a dry-run request.
- [ ] Show normalized input, applicable policy rules, registry/certification revisions, candidate eligibility, reason codes, selected identity, limitations, and evidence references.
- [ ] Clearly distinguish facts, policy decisions, unknown/unavailable evidence, and waived controls.
- [ ] Support machine-readable output plus a human view; enforce authorization for sensitive diagnostic fields.
- [ ] Golden-test explanations so refactors cannot silently drop critical decision context.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts
- [ ] observability / operations integration

---

### MC-064 — Release-lineage/infrastructure-graph correlation

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Implement **Release-lineage/infrastructure-graph correlation** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define identifiers for application release, workload release, site/infrastructure graph revision, image/build artifact, and selection decision.
- [ ] Accept or resolve those identifiers at integration boundaries and persist them in the decision/audit record.
- [ ] Link downstream INV-27 execution events back to the same lineage without trusting mutable display names.
- [ ] Specify behavior when graph/release metadata is unavailable or stale.
- [ ] Test correlation through selection → build/execution and during rollback/incident scenarios.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] observability / operations integration

---

### MC-065 — Telemetry retention/sampling/privacy/export policy

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Implement **Telemetry retention/sampling/privacy/export policy** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Write a telemetry policy specifying data classes, permitted fields, retention periods, sampling, storage/export destinations, access controls, deletion requirements, and incident overrides.
- [ ] Define separate rules for metrics, logs, traces, decision audit records, security evidence, and benchmark data.
- [ ] Document tenant/workload privacy boundaries and cross-region/export restrictions if applicable.
- [ ] Encode enforceable settings where possible instead of relying only on prose.
- [ ] Add policy tests/config validation and periodic review/expiry dates.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls
- [ ] observability / operations integration

---

### MC-066 — Dashboards and alert definitions

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Implement **Dashboards and alert definitions** so operators and automation can observe/explain INV-28 without weakening privacy or correctness.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create dashboards for catalog health, selectable toolchains, stale reviews/certifications, selection/refusal rate, reason-code distribution, latency, dependency health, integrity failures, and lifecycle states.
- [ ] Create alerts with severity/runbook links for security review expiry, signature failure, sudden refusal spikes, dependency outage, registry drift, unsafe state transitions, and SLO breaches.
- [ ] Define alert thresholds from SLO/error budgets/capacity tests rather than arbitrary values.
- [ ] Test alert rules using synthetic metrics/logs and prevent duplicate/noisy pages.
- [ ] Version dashboard/alert definitions in repository and include them in release review.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] observability / operations integration

---

## F. Resilience and operational gaps

### MC-067 — Persistent backup/restore/reconstruction procedure

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no registry persistence means no implemented backup/restore mechanism.  
**Target state:** Implement **Persistent backup/restore/reconstruction procedure** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] After implementing persistent registry state, define backup scope: registry/catalog, policy/waivers, decision ledger, signing metadata references, migration state, and required evidence.
- [ ] Specify RPO/RTO, backup frequency, encryption, retention, access control, and off-site/independent storage expectations.
- [ ] Provide deterministic reconstruction from signed catalog + policy + certification snapshots where full backup is unnecessary.
- [ ] Automate restore verification into an isolated environment and validate signatures/revisions after restore.
- [ ] Document corruption/partial-backup handling and run scheduled recovery exercises.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] persistent state / lifecycle / recovery design

---

### MC-068 — Canary/staged rollout implementation

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** README references gate behavior generally, but there is no component-specific rollout automation.  
**Target state:** Implement **Canary/staged rollout implementation** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define how a new INV-28 package/catalog/policy version is promoted through dev/test/canary/staged production rings.
- [ ] Gate each stage on compatibility, security, telemetry health, refusal-rate change, and exact artifact/evidence identity.
- [ ] Keep rollout state externalized/persistent and idempotent; support pause/resume/abort.
- [ ] Ensure catalog changes and code changes can be rolled independently when policy permits.
- [ ] Exercise successful and failed canaries, partial site rollout, and rollback in automation/tests.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] persistent state / lifecycle / recovery design

---

### MC-069 — Rollback implementation

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** prose references an evidence head, but no component-owned rollback command/state transition exists.  
**Target state:** Implement **Rollback implementation** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Implement rollback to a specific prior signed component/catalog/policy revision rather than an informal 'previous evidence head'.
- [ ] Validate target revision compatibility and integrity before activation; prevent rollback to revoked/vulnerable state unless an explicit emergency policy allows it.
- [ ] Make state transitions atomic and auditable with actor/reason/change record.
- [ ] Preserve historical decisions and ledger continuity across rollback.
- [ ] Test rollback during active selection load, failed migration, and partially deployed rollout.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] persistent state / lifecycle / recovery design

---

### MC-070 — Emergency-disable implementation

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** prose says remove from registry package; no explicit disable/quarantine state or safe administrative operation exists.  
**Target state:** Implement **Emergency-disable implementation** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add explicit quarantine/disabled lifecycle state and an administrative operation that can block one toolchain/version/profile immediately without deleting history.
- [ ] Support scope (global/site/environment) and reason/incident reference plus automatic/explicit expiry policy.
- [ ] Make selection consult emergency state before lower-priority allow rules and emit a stable refusal/elimination code.
- [ ] Propagate emergency disable through caches quickly with measurable convergence.
- [ ] Test unauthorized disable, repeated/idempotent disable, disable during rollout, recovery/re-enable, and stale-node behavior.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls
- [ ] persistent state / lifecycle / recovery design

---

### MC-071 — Supported-version compatibility matrix

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Implement **Supported-version compatibility matrix** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Publish a generated compatibility matrix covering INV-28 version, `pk_core`, schema interfaces, catalog schema, GAP-15, INV-27, GAP-08 when used, Python runtime, toolchain versions/profiles, architectures, VMMs, and providers.
- [ ] Distinguish tested/certified, supported-with-constraints, deprecated, and unsupported states.
- [ ] Generate rows from test/certification evidence where possible and link evidence IDs.
- [ ] Define compatibility policy for patch/minor upgrades and breaking changes.
- [ ] Fail release if declared support has no current evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-072 — Patching/vulnerability-response/EOL SLAs

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent as an operational policy artifact.  
**Target state:** Implement **Patching/vulnerability-response/EOL SLAs** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define patch timelines by vulnerability severity/exploitability and separate upstream dependency/toolchain issues from INV-28 code issues.
- [ ] Define acknowledgement, triage, mitigation, fix, release, and customer/operator communication targets.
- [ ] Define EOL notice windows, final supported versions, and emergency revocation procedure.
- [ ] Connect SLA clocks to advisory ingestion, incident tracking, lifecycle state, and waiver expiry.
- [ ] Measure SLA compliance and review exceptions in operations governance.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-073 — Incident response runbook

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no severity, paging, escalation, containment, recovery document.  
**Target state:** Implement **Incident response runbook** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create an incident runbook with severity taxonomy, triggers, paging/escalation tree, decision authority, evidence preservation, containment, recovery, and post-incident review.
- [ ] Include scenarios for unsafe toolchain selection, registry/signature compromise, stale/false certification, widespread refusals, dependency outage, data corruption, and compromised release.
- [ ] Define immediate containment actions such as quarantine, policy deny, catalog rollback, and key revocation.
- [ ] Provide exact diagnostic queries/commands that are safe in production and link dashboards/explain tooling.
- [ ] Run tabletop/game-day exercises and record corrective actions.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls
- [ ] observability / operations integration

---

### MC-074 — Recurring review automation

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no job/workflow for access, policy, dependency, configuration, architecture, or security-review freshness.  
**Target state:** Implement **Recurring review automation** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create scheduled automation to review registry entries, security review freshness, certifications, dependency/advisory state, policies/waivers, access/owners, schema compatibility, and architecture assumptions.
- [ ] Generate actionable findings with owners/severity/due dates instead of only a pass/fail email.
- [ ] Auto-quarantine or fail production gates for mandatory expired controls according to policy.
- [ ] Retain immutable review evidence and diff against the previous review.
- [ ] Test scheduler failure, duplicate runs, clock skew, and missed-run recovery.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls
- [ ] persistent state / lifecycle / recovery design

---

### MC-075 — Technical-debt/deprecation register

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Implement **Technical-debt/deprecation register** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create a machine-readable debt/deprecation register with ID, description, affected components/versions, risk, owner, creation date, target date, status, dependencies, and expiry/review date.
- [ ] Link code TODOs, waivers, deprecated schema fields, lifecycle states, and known limitations to register IDs.
- [ ] Prevent expired high-risk debt/waivers from silently passing production gates.
- [ ] Review debt on releases and recurring governance cadence.
- [ ] Archive closure evidence and avoid deleting history.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] persistent state / lifecycle / recovery design

---

### MC-076 — Formal production exit-gate artifact

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** depends on external `pk_core`; no resulting gate report is shipped.  
**Target state:** Implement **Formal production exit-gate artifact** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Generate and ship the real `pk_core gate INV-28` result (or successor gate format) for each release.
- [ ] Bind the gate artifact to exact source/build/package/catalog/policy/dependency/evidence digests.
- [ ] Ensure all 100 checklist requirements have explicit status and evidence; blocked/unknown cannot become silent pass.
- [ ] Sign/attest the gate artifact and verify it at promotion/deployment.
- [ ] Add CI logic that refuses release publication when the formal exit gate is not GO under the declared policy.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path
- [ ] security/evidence/provenance controls

---

### MC-077 — Capacity model and saturation thresholds

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Implement **Capacity model and saturation thresholds** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define workload assumptions and capacity dimensions: registry entries, versions/profiles per toolchain, capabilities/device cardinality, sites, concurrent requests, mutation rate, audit-log rate, and dependency latency.
- [ ] Benchmark and derive saturation thresholds for CPU, memory, persistence, queue/backlog, cache, and telemetry output.
- [ ] Define headroom and overload behavior; selection safety must be preserved under saturation.
- [ ] Expose saturation metrics and alerts and document scaling strategy.
- [ ] Revalidate the model after algorithm/schema/persistence changes and with fleet-scale tests.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] observability / operations integration

---

### MC-078 — Resource bounds

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no bounds on registry size, input token lengths, elimination-output size, or selection work.  
**Target state:** Implement **Resource bounds** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Set explicit validated bounds for names/tokens, number of languages/architectures/capabilities/devices/limitations, registry entries, candidates, policy rules, waiver count, diagnostic strings, and eliminated-result size.
- [ ] Bound algorithmic work and memory per request; identify worst-case complexity and reject pathological inputs early.
- [ ] Define truncation/pagination for operator diagnostics without weakening the actual decision evaluation.
- [ ] Add property/fuzz tests at just-below, exactly-at, and above each bound.
- [ ] Return stable validation/resource-limit codes and metrics for rejected oversized input.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-079 — Timeout/cancellation semantics

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent (currently local/synchronous, but no defined boundary for future external checks).  
**Target state:** Implement **Timeout/cancellation semantics** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define deadlines/cancellation behavior for selection and every future external lookup (certification, persistence, policy, provenance) while keeping pure local evaluation deterministic.
- [ ] Propagate caller deadlines where interfaces support them and set stricter internal maximums.
- [ ] Specify whether timeout causes fail-closed refusal, degraded last-known-good evaluation, or retriable dependency error for each dependency class.
- [ ] Ensure cancellation cannot leave partial registry mutations or incomplete audit records that appear committed.
- [ ] Test timeout races, cancellation before/after commit point, dependency recovery, and retry idempotency.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] persistent state / lifecycle / recovery design

---

### MC-080 — Cache/locality behavior

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no compatibility-result cache or defined invalidation strategy.  
**Target state:** Implement **Cache/locality behavior** as an operationally testable resilience/governance capability with explicit failure behavior.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Identify cacheable data such as parsed catalog, verified signatures, certification lookup, compatibility intersections, and policy compilation.
- [ ] Define cache key to include every safety-relevant revision/digest; never key only on toolchain name.
- [ ] Set TTL/freshness semantics and explicit invalidation on quarantine, advisory, policy, catalog, certification, or key changes.
- [ ] Prevent stale cache from bypassing emergency disable/revocation; define push invalidation or short maximum staleness for critical state.
- [ ] Instrument hit/miss/staleness and test invalidation races plus cold-start behavior.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Inject partial failure/restart/retry and confirm state remains consistent and the operation is idempotent or explicitly non-retriable.
- [ ] Confirm the documented rollback/emergency path can be executed without deleting audit history.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] persistent state / lifecycle / recovery design
- [ ] observability / operations integration

---

## G. Packaging, automation, and repository hygiene gaps

### MC-081 — CI workflow

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no GitHub Actions/Azure Pipelines/etc. configuration.  
**Target state:** Add **CI workflow** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add CI workflow(s) for supported Python/OS matrix as appropriate, with clean checkout/install and no undeclared local dependencies.
- [ ] Run compile/import, unit, schema/contract, integration where dependencies are available, type/lint/static/security scans, coverage, optimized-mode tests, package build, and gate verification.
- [ ] Use least-privilege credentials and protected environments for signing/release stages.
- [ ] Cache only dependency downloads/build outputs safely; do not cache mutable security decisions.
- [ ] Publish machine-readable artifacts and make mandatory jobs required for merge/release.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path

---

### MC-082 — Reproducible environment/lockfile

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Add **Reproducible environment/lockfile** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Choose a single reproducible dependency-resolution strategy and commit lock/hashes for runtime and tooling dependencies.
- [ ] Pin the supported Python minor range and test resolver output in a clean environment.
- [ ] Separate development/test/release dependency groups while keeping the release dependency graph minimal.
- [ ] Record dependency lock digest in provenance and acceptance evidence.
- [ ] Add an automated controlled update workflow with diffed vulnerability/license/test results.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path

---

### MC-083 — Build/package configuration

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Add **Build/package configuration** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add build configuration in `pyproject.toml`, package discovery, version source, included data files/schemas/catalog defaults, and build backend.
- [ ] Produce wheel and sdist; inspect contents to ensure required schemas/policies/licenses are included and tests/dev junk are excluded per policy.
- [ ] Make versioning single-source and verify `VERSION`, package `__version__`, README/changelog references, and artifact metadata agree.
- [ ] Test installation/import/execution from built artifacts in a clean virtual environment.
- [ ] Define platform independence or platform-specific wheels explicitly.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path

---

### MC-084 — Release automation

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Add **Release automation** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Automate version/tag validation, clean build, full gates, SBOM, scans, provenance/signing, checksum manifest, release notes, artifact publication, and post-publish verification.
- [ ] Use immutable tags and protected release credentials; prohibit publishing from dirty/unverified worktrees.
- [ ] Make reruns idempotent and prevent overwriting an existing version with different bytes.
- [ ] Attach gate/acceptance evidence and compatibility matrix to the release.
- [ ] Test release automation in a non-production/staging repository or dry-run path.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path
- [ ] security/evidence/provenance controls

---

### MC-085 — Generated artifact/checksum manifest

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** absent.  
**Target state:** Add **Generated artifact/checksum manifest** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Generate a release manifest listing every distributable artifact/evidence file with relative name, media/type, size, cryptographic digest/algorithm, schema version where relevant, and provenance/signature reference.
- [ ] Include wheel/sdist/source archive, SBOM, schemas, catalog/policy snapshots if shipped, test/gate results, coverage/security reports, and documentation bundle as applicable.
- [ ] Canonicalize manifest ordering and sign/attest the manifest.
- [ ] Verify manifest immediately after build and again after publication/download.
- [ ] Reject unexpected/missing artifacts or digest mismatches.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

### MC-086 — Code-format/lint configuration

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Add **Code-format/lint configuration** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add repository-local formatter/linter configuration with pinned versions and documented commands.
- [ ] Define line length, import ordering, target Python version, selected rule sets, and narrowly justified ignores.
- [ ] Run formatting in check mode and lint in CI; optionally provide auto-fix developer command.
- [ ] Ensure generated/vendor files are excluded explicitly rather than via broad directories that hide source.
- [ ] Baseline current code cleanly and prevent new warnings from accumulating.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-087 — Type-checking configuration

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent despite type annotations.  
**Target state:** Add **Type-checking configuration** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Configure strict static type checking for `Toolchain`, registry, request/result/refusal/policy models, serializers, and integration adapters.
- [ ] Eliminate bare `dict` return types and untyped collections on public APIs as structured models are introduced.
- [ ] Define typed protocols/interfaces for persistence, certification, policy, metrics/logging, and clock sources.
- [ ] Use targeted suppressions with reasons rather than global permissive flags.
- [ ] Run type checking in CI and add tests for runtime schema/type boundary alignment.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-088 — Pre-commit hooks

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Add **Pre-commit hooks** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add pre-commit hooks for formatting, lint, type/static checks appropriate to commit latency, schema validation, JSON/YAML formatting, secret scanning, and common repository hygiene.
- [ ] Pin hook revisions and document update procedure.
- [ ] Keep expensive integration/security/fuzz jobs in CI while providing optional local hooks.
- [ ] Add custom checks for version consistency and `CHECKLIST.json`/`MASTER.md` completeness if needed.
- [ ] Verify hooks run identically on Windows-supported developer workflows and CI where portability is required.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-089 — Developer setup instructions

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** README assumes `pk_core` exists but does not provide a deterministic install/bootstrap path.  
**Target state:** Add **Developer setup instructions** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Write deterministic setup instructions from a clean machine: supported Python, environment creation, dependency install, `pk_core` acquisition, test commands, gate commands, build, and troubleshooting.
- [ ] Provide Windows-safe PowerShell/CMD examples if Windows is a supported development environment, alongside portable shell/Python commands.
- [ ] Document offline installation/wheelhouse path if required and how to validate installed versions/digests.
- [ ] Include expected successful outputs and common failure diagnoses such as missing/incompatible `pk_core`.
- [ ] Continuously test the documented bootstrap in CI to prevent documentation drift.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `pk_core` packaging/conformance path

---

### MC-090 — Architecture/design document

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** no dedicated data-flow, trust-boundary, lifecycle, or dependency diagram/document.  
**Target state:** Add **Architecture/design document** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create `ARCHITECTURE.md` describing responsibility/non-goals, domain model, register lifecycle, selection pipeline, policy evaluation, certification dependency, integrity verification, persistence, observability, and downstream handoff.
- [ ] Add data-flow and trust-boundary diagrams plus sequence diagrams for register/update, selection/refusal, emergency disable, rollout, and rollback.
- [ ] Document source-of-truth hierarchy and revision identities for catalog, policy, certification, and evidence.
- [ ] Record key design decisions/trade-offs in ADRs, especially policy maturity semantics and time model.
- [ ] Link architecture sections to threat model, interfaces, and tests.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-091 — Schema/version migration plan

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** no plan for registry/interface schema evolution.  
**Target state:** Add **Schema/version migration plan** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Normative documentation/policy artifact.
- [ ] Machine-readable schema/configuration.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define independent versioning for Python package, registry schema, request/result interfaces, policy schema, decision ledger, and evidence formats.
- [ ] Specify backward/forward compatibility guarantees and exact triggers for major version increments.
- [ ] Provide migration functions/tools with validation, dry-run, backup, rollback, and idempotency semantics.
- [ ] Test migrations from every supported prior schema version using golden fixtures and corrupted/partial inputs.
- [ ] Record migration version/revision in persisted state and block downgrade when incompatible.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] versioned interface/schema artifacts
- [ ] persistent state / lifecycle / recovery design

---

### MC-092 — Examples/fixtures directory

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** absent.  
**Target state:** Add **Examples/fixtures directory** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Create `examples/` and `tests/fixtures/` with clearly separated non-production data.
- [ ] Include valid MirageOS/Unikraft/OSv/Nanos records, multi-version/profile examples, site/workload requests, successful selections, refusals, stale review, EOL/quarantine, bad signatures, and certification mismatch.
- [ ] Ensure fixtures are schema-valid (or intentionally invalid with expected error metadata) and deterministic.
- [ ] Mark example credentials/signatures as non-secret/test-only and prevent fixtures from loading into production by default.
- [ ] Use fixtures across docs, schema tests, property tests, and integration tests to reduce drift.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-093 — Changelog release links/evidence references

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** changelog describes gates but does not point to immutable test/evidence artifacts.  
**Target state:** Add **Changelog release links/evidence references** to make the repository reproducible, maintainable, releasable, and independently auditable.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Add immutable links/references from each changelog release entry to source tag/commit, build manifest, checksums/signatures, SBOM, test/gate results, security scan summaries, compatibility matrix, and acceptance evidence.
- [ ] Prefer content-addressed artifact IDs/digests over mutable 'latest' URLs.
- [ ] Record breaking schema/policy changes and migration requirements explicitly.
- [ ] Add a release-validation check ensuring referenced evidence exists and matches the release digest.
- [ ] Keep human-readable changelog concise while the manifest carries exhaustive machine evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] security/evidence/provenance controls

---

## H. Scope/contract inconsistencies still requiring an upstream decision

### MC-094 — Production maturity policy ambiguity

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** Contract boundary text says production “may permit only mature toolchains,” while mandatory logic only excludes `experimental`, so `beta` remains selectable.  
**Target state:** Close the unresolved contract/implementation decision for **Production maturity policy ambiguity** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Resolve the normative policy question: in production, is `beta` allowed, conditionally allowed, or prohibited so only `mature` is selectable? Record the decision in an ADR/contract revision.
- [ ] Align `contract.py` boundary text, mandatory requirements, policy schema/defaults, README, tests, and SLO language to one interpretation.
- [ ] Do not encode the outcome only as a code constant; represent it in versioned policy with stable refusal code.
- [ ] Add explicit tests for experimental/beta/mature under production and non-production environments, including waiver behavior if permitted.
- [ ] Treat a change in this policy as safety-relevant and require compatibility/release notes plus gate evidence.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path

---

### MC-095 — OSv catalog representation

**Priority:** P2 — maturity / assurance / developer-experience  
**Audit gap:** OSv is named in repository documentation but not represented by any shipped registry entry or fixture.  
**Target state:** Close the unresolved contract/implementation decision for **OSv catalog representation** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Decide whether OSv is actually supported, planned, example-only, or should be removed from normative repository wording.
- [ ] If supported, add pinned OSv version/profile catalog entries with architectures, provider/VMM/device/ABI capabilities, lifecycle, security posture, review provenance, integrity identity, and GAP-15 certification.
- [ ] If not currently supported, mark it explicitly as unregistered/unselectable and avoid documentation implying operational support.
- [ ] Add OSv fixtures and matrix/integration coverage only for claims that are backed by evidence.
- [ ] Add a documentation/catalog consistency test so named supported toolchains cannot silently lack registry representation.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior

---

### MC-096 — Production review time/provenance model

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** Review time uses abstract logical ticks rather than wall-clock timestamps and verifiable provenance.  
**Target state:** Close the unresolved contract/implementation decision for **Production review time/provenance model** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Adopt an injectable UTC clock/time-source abstraction for production decisions while preserving deterministic tests with a fake clock.
- [ ] Store timezone-aware UTC timestamps and review expiry; define precision, acceptable clock skew, and behavior when trusted time is unavailable.
- [ ] Bind review records to reviewer/evidence provenance and do not treat a timestamp alone as proof of review.
- [ ] Migrate logical tick fixtures into test-only constructs or schema-versioned legacy data with a clear conversion policy.
- [ ] Test expiry boundaries, future timestamps, clock rollback/jump, serialization, and replay using historical decision time.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] security/evidence/provenance controls

---

### MC-097 — GAP-15 certification consumption

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** Toolchain selection does not consume `GAP-15` certification output and currently trusts local fields only.  
**Target state:** Close the unresolved contract/implementation decision for **GAP-15 certification consumption** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define the exact GAP-15 output schema consumed by INV-28: toolchain/version/profile/artifact identity, architecture/platform/VMM/device/capability tuple, certification status, evidence digest, issuance/expiry, and revocation.
- [ ] Implement a verification adapter that authenticates GAP-15 data and normalizes it into an immutable certification snapshot.
- [ ] Make production `select()` intersect local catalog claims with valid GAP-15 certification and fail closed on missing/mismatched/expired data.
- [ ] Record the certification snapshot/version/digest in `SelectionResult` and decision ledger.
- [ ] Test stale cache, revoked certification, partial certification, interface-version mismatch, and dependency outage policy.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] versioned interface/schema artifacts
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] security/evidence/provenance controls

---

### MC-098 — Selection/build anti-substitution enforcement

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** The selected record contains no immutable artifact/toolchain digest for downstream binding.  
**Target state:** Close the unresolved contract/implementation decision for **Selection/build anti-substitution enforcement** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Carry immutable toolchain/artifact digest plus signing/provenance identity from catalog through `SelectionResult` to the build/execution request.
- [ ] Require the consumer (INV-27/build stage) to verify that exact digest/signature before execution and reject same-name/version substitutions.
- [ ] Bind decision ID, request digest, catalog revision, certification reference, and artifact digest into signed/tamper-evident evidence.
- [ ] Define TOCTOU protections for artifact retrieval and cache: verify after download and immediately before use as appropriate.
- [ ] Create adversarial integration tests replacing artifacts/manifests between selection and execution.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.
- [ ] Tamper with or stale the relevant security/evidence artifact and confirm verification fails closed.
- [ ] Verify key/credential/secret material is not embedded in logs, fixtures, source control, or release evidence.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source
- [ ] security/evidence/provenance controls

---

### MC-099 — Site-boundary enforcement

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** The contract says a site supports a subset of architectures, but `select()` receives no site capability context.  
**Target state:** Close the unresolved contract/implementation decision for **Site-boundary enforcement** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define a structured `SiteCapabilities`/site context containing supported architectures, VMMs, device classes, providers/platforms, policy scope, and capability snapshot revision.
- [ ] Pass site context or an authenticated site-capability reference into `SelectionRequest`; do not infer site solely from architecture.
- [ ] Intersect site capabilities with workload requirements, catalog claims, and GAP-15 certification before selection.
- [ ] Record site capability snapshot ID in decision evidence while respecting tenancy/privacy boundaries.
- [ ] Test cross-site differences, stale site data, unsupported architecture despite toolchain support, and site capability changes during rollout.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

### MC-100 — Workload feature-needs modeling

**Priority:** P0 — production blocker / integrity-critical  
**Audit gap:** The workload boundary says workloads declare language and feature needs, yet `select()` accepts only language, architecture, environment, and logical time.  
**Target state:** Close the unresolved contract/implementation decision for **Workload feature-needs modeling** with one explicit, versioned, testable behavior; remove ambiguity from production selection.

**Required deliverables**
- [ ] Machine-readable schema/configuration.
- [ ] Production implementation.
- [ ] Automated tests/gates.
- [ ] Release evidence with immutable references/digests.

**Implementation checklist**
- [ ] Define `WorkloadRequirements` with required/optional language runtime/profile, capabilities, devices, ABI/protocol, resource/boot constraints, environment, and any placement-independent requirements owned by INV-28.
- [ ] Specify requirement semantics (must, prefer, forbid, version/range) and canonical normalization so policy decisions are deterministic.
- [ ] Refactor selection to evaluate the complete requirement object and emit stable per-constraint elimination codes.
- [ ] Add property tests proving no selected toolchain lacks a required feature and no forbidden capability/limitation conflict is ignored.
- [ ] Coordinate the boundary with upstream workload specification and downstream INV-27 so fields are neither duplicated inconsistently nor dropped.
- [ ] Assign a named owner/codeowner and document the authoritative source of truth for this component.
- [ ] Define versioning/compatibility and migration behavior before production data or interfaces depend on it.
- [ ] Use deterministic normalization/serialization and fail closed on malformed, unknown, stale, unauthenticated, or unsupported production inputs.
- [ ] Update README/architecture/contract documentation wherever this component changes declared behavior or boundaries.

**Verification / negative-test checklist**
- [ ] Add positive, boundary, and negative tests; every safety-sensitive refusal must be asserted by stable code/state, not fragile message text.
- [ ] Run tests from a clean installed build with pinned dependencies; include `python -O` where optimizer behavior could matter.
- [ ] Add CI/release gating so the component cannot regress or disappear without a visible failure.
- [ ] Exercise malformed/oversized/untrusted input and verify bounded resource use, deterministic errors, and no secret/sensitive-data leakage where applicable.
- [ ] Prove a matching-looking but unsafe/incomplete candidate is rejected with a stable machine-readable reason.
- [ ] Prove selection output contains enough immutable identity/revision data to replay and independently verify the decision.

**Acceptance / production gate**
- [ ] Implementation, schema/configuration, tests, and documentation all agree on one behavior; no contradictory defaults remain.
- [ ] Mandatory failure modes produce explicit non-success outcomes; unknown or missing evidence cannot be interpreted as compatible/safe.
- [ ] The change is exercised in the real release/conformance path, not only by mocks or assessment-code examples.
- [ ] A reviewer independent of the implementation verifies the evidence and signs/approves the change according to repository governance.

**Evidence to retain**
- [ ] Store machine-readable test/gate output with component version, source revision, dependency lock digest, schema/policy revisions, timestamp, and tool versions.
- [ ] Record content digests for relevant artifacts and link them from the release manifest/changelog or acceptance record.
- [ ] Document any residual risk, approved exception/waiver, owner, and expiry; unresolved mandatory controls remain NO_GO.

**Primary repository / integration touch-points**
- [ ] `README.md` / `CHANGELOG.md` for externally visible behavior
- [ ] `component.py` domain model / selection path
- [ ] versioned interface/schema artifacts
- [ ] adjacent components: GAP-15 / INV-27 / GAP-08 / site capability source

---

## Final repository-wide closure gate

- [ ] All MC-001 through MC-100 items have an owner and explicit status.
- [ ] All P0 items are complete with no expired waiver or unresolved ambiguity.
- [ ] All interface and persistence schemas are versioned, validated, and migration-tested.
- [ ] `pk_core` is installed reproducibly and the real 100-check conformance/gate/verify path passes from a clean built artifact.
- [ ] Selection consumes authenticated GAP-15 certification and emits an immutable toolchain/version/profile/artifact identity that INV-27 verifies.
- [ ] Production policy for `beta` vs `mature` is explicitly decided and tested.
- [ ] Site capabilities and workload feature requirements are first-class inputs to selection.
- [ ] Registry/catalog/policy/certification/evidence revisions are authentic, integrity-checked, and replayable.
- [ ] Security scans, threat-derived tests, compatibility matrices, optimized-mode tests, coverage/mutation evidence, performance/resilience evidence, and rollback/emergency tests meet declared gates.
- [ ] Health/status/metrics/logs/traces/decision ledger/explain views are operational and privacy-safe.
- [ ] Rollout, rollback, emergency disable, incident response, backup/reconstruction, recurring review, and EOL procedures have been exercised rather than only documented.
- [ ] Release manifest, SBOM, provenance/signatures/checksums, formal production gate, and machine-readable acceptance evidence all bind to the same exact release bytes.
- [ ] README, architecture, contract, schemas, examples, changelog, compatibility matrix, and operational runbooks accurately describe the shipped behavior.
- [ ] No declared supported toolchain/version/profile/platform exists without current verifiable compatibility/security evidence.
- [ ] No remaining mandatory item is marked unknown, skipped, inherited, or satisfied solely by prose.

**Release verdict rule:** production GO only when all mandatory gates above are satisfied or an explicitly waivable control has a scoped, approved, unexpired waiver recorded in the acceptance evidence. Any missing integrity identity, unverified production certification, policy ambiguity affecting safety, or inability to reproduce/verify the release remains **NO_GO**.