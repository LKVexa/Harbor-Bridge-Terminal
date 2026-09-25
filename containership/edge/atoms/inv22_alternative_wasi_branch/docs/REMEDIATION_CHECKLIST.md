# INV-22 v4.2.0 — Missing Components Engineering Remediation Checklist

**Repository:** `inv22_alternative_wasi_branch`  
**Baseline:** v4.2.0 hardened audit, 2026-09-23  
**Source gap inventory:** `MISSING_COMPONENTS.md` (64 missing or externally unresolved components)  
**Control set:** `CHECKLIST.json` (`INV-22-C001` through `INV-22-C100`)  

## Purpose

This document converts every item in the post-hardening missing-component audit into an implementation-ready engineering work package. Each work package contains a target state, concrete implementation tasks, verification/negative tests, mandatory evidence, and an explicit exit condition. The intent is to make the remaining work auditable and release-gateable rather than leaving it as narrative technical debt.

### Priority convention

- **P0 — release/security/invariant blocker:** must be resolved (or covered by an explicitly permitted, time-bounded formal waiver) before production certification.
- **P1 — production-readiness requirement:** required for a professionally operated production implementation; may be sequenced after foundational P0 work but should remain in the production exit plan.
- **P2/P3:** none assigned here because every item came from the repository's post-hardening missing-component audit; optional enhancements should be tracked separately rather than diluting this remediation ledger.

### Global definition of done

Before any individual work package is marked complete, its implementation should satisfy all of the following where applicable:

- [ ] The implementation is version-controlled, reviewed, and linked to the exact INV-22 control IDs listed in that work package.
- [ ] Public/external behavior is represented by a versioned typed contract rather than undocumented Python object behavior.
- [ ] Security-critical uncertainty fails closed; no missing classification, unsupported version, stale trust state, or invalid configuration is silently accepted.
- [ ] Positive, negative, boundary, and adversarial tests exist and run automatically in CI.
- [ ] Persistent state changes are atomic/recoverable and generate attributable audit evidence.
- [ ] Telemetry is structured, bounded in cardinality, and redacts secrets/payload data by default.
- [ ] The exact artifact/config/schema/baseline/dependency revisions used by tests are captured in machine-readable evidence.
- [ ] Any exception is represented by the formal waiver mechanism with scope, owner, approver, compensating controls, and expiry.
- [ ] Documentation/runbooks are updated when the implementation changes operator-visible behavior.
- [ ] The production exit gate consumes the generated evidence rather than relying on manual assertions.

## Recommended dependency order

1. **Foundations:** MC-01–MC-08, MC-11–MC-16, MC-20, MC-25, MC-29, MC-31.
2. **Trust and state:** MC-09–MC-10, MC-18–MC-24, MC-26–MC-28, MC-41, MC-43–MC-44, MC-63.
3. **Verification:** MC-30, MC-32–MC-38, MC-51–MC-55.
4. **Operations/release:** MC-39–MC-40, MC-42, MC-45–MC-50, MC-56–MC-62.
5. **Final evidence:** MC-64.

---

## MC-01 — `pk_core` runtime/framework dependency

**Priority:** P0 — release blocker  
**Related INV-22 controls:** C020, C030, C040, C081–C090, C100  

**Target state:** Make the parent execution/evidence framework a reproducible, versioned dependency so INV-22 can execute its full assessment, evidence, gate, and verification path locally and in CI.

### Implementation checklist

- [ ] Choose the supported `pk_core` consumption model: published package, Git commit/tag dependency, vendored subtree, or workspace sibling; document exactly one canonical production path and one development override path.
- [ ] Pin `pk_core` to an immutable version and artifact digest/commit SHA; prohibit floating branches such as `main`, unbounded version ranges, or implicit `PYTHONPATH` discovery in release builds.
- [ ] Declare the dependency in package metadata and expose the required API surface/version contract for `pk_core.contract`, `pk_core.checklist`, `pk_core.component`, evidence emission, gate execution, registry discovery, and verification.
- [ ] Add a startup/preflight compatibility check that reports installed `pk_core` version, expected API level, discovered registry path, and a machine-readable incompatibility code before any assessment runs.
- [ ] Remove the current “skip when unavailable” behavior from production CI; retain skip only for an explicitly labeled minimal-core test job and fail the full-conformance job if `pk_core` cannot be imported.
- [ ] Define how `PK_CORE_PATH` is accepted in development, canonicalize it, reject nonexistent/untrusted paths, and ensure release CI never depends on a developer-local path.
- [ ] Add a hermetic fixture or test package that exercises `COMPONENT.assess_all()`, evidence JSONL generation, `pk_core gate`, and `pk_core verify` against INV-22.
- [ ] Document upgrade compatibility rules and a rollback procedure for `pk_core` version changes; require an integration test before bumping the pin.

### Verification and negative-test checklist

- [ ] From a clean environment, install INV-22 and its locked dependencies and run the complete `tests/test_component.py` without skips.
- [ ] Run `python -m pk_core run INV-22`, `gate`, and `verify`; assert exit codes, schema-valid outputs, and evidence-chain continuity.
- [ ] Negative-test an unsupported `pk_core` API version and an absent dependency; both must fail closed with actionable diagnostics.
- [ ] Run the same conformance path under optimized Python (`-O`) to prove no correctness gate relies on `assert`.

### Required evidence/artifacts

- [ ] Locked dependency record containing exact `pk_core` version and integrity identifier.
- [ ] CI artifact containing complete conformance logs, evidence ledger, gate result, and verification result.
- [ ] Compatibility/preflight report proving the runtime API level used for the release.

### Exit criterion

- [ ] **DONE only when:** All three supplied conformance tests execute rather than skip, full `pk_core` run/gate/verify succeeds from a clean checkout, and the dependency is immutable and reproducible.

---

## MC-02 — Adjacent architecture dependencies

**Priority:** P0 — integration blocker  
**Related INV-22 controls:** C003, C020, C030, C083, C093, C100  

**Target state:** Make INV-13, INV-11, INV-12, INV-10, and GAP-14 explicit, versioned integration contracts with executable compatibility checks.

### Implementation checklist

- [ ] Create a dependency manifest with one record per adjacent element: element ID, role (upstream/peer/downstream), supported versions, contract/schema versions, owner, endpoint/package identity, and failure policy.
- [ ] Define the exact data/control flow between INV-22 and each dependency: interface-definition ingestion from INV-13/INV-11, ABI mapping reuse from INV-12, branch-link enforcement by INV-10, and certification handoff to GAP-14.
- [ ] Pin each dependency to a release/commit/schema digest and record the minimum/maximum compatible versions; treat unknown versions as incompatible until proven.
- [ ] Provide adapters/ports rather than importing implementation internals so adjacent elements can evolve independently behind stable typed contracts.
- [ ] Define dependency-unavailable behavior separately for build time, certification time, deployment time, and runtime; security-critical absence must fail closed.
- [ ] Add contract-test fixtures owned jointly at the boundary, including valid, boundary-version, malformed, and semantically incompatible examples.
- [ ] Implement a dependency status command/report that exposes resolved versions, schema digests, health, and compatibility verdicts.
- [ ] Document ownership and escalation for breaking changes and require coordinated change review when a dependency changes a contract consumed by INV-22.

### Verification and negative-test checklist

- [ ] Run integration tests against the minimum and maximum supported version of every adjacent dependency.
- [ ] Inject a mismatched schema/version for each dependency and verify INV-22 rejects it before certification or activation.
- [ ] Simulate each dependency being unavailable and assert the documented degraded/fail-closed behavior.

### Required evidence/artifacts

- [ ] Machine-readable dependency compatibility matrix.
- [ ] Boundary contract fixtures and CI integration-test reports.
- [ ] Release evidence listing exact adjacent component versions/digests.

### Exit criterion

- [ ] **DONE only when:** Every adjacent dependency has a pinned, tested contract and INV-22 can prove interoperability or produce a deterministic incompatibility verdict.

---

## MC-03 — Package/build metadata

**Priority:** P0 — reproducibility blocker  
**Related INV-22 controls:** C016, C031, C032, C040, C050, C100  

**Target state:** Turn the source tree into a standards-compliant, installable Python package with deterministic wheel/sdist production and explicit runtime/toolchain constraints.

### Implementation checklist

- [ ] Add `pyproject.toml` using a PEP 517 build backend and declare project name, version source, description, package discovery, license metadata, authors/maintainers, URLs, and classifiers as applicable.
- [ ] Declare `requires-python` based on tested interpreters rather than developer assumptions; fail installation on unsupported versions.
- [ ] Separate runtime, test, lint/type, security, and documentation dependencies into clearly named dependency groups/extras.
- [ ] Ensure the package namespace/layout installs `inv22_alternative_wasi_branch` correctly and includes required non-code artifacts such as `CHECKLIST.json`, schemas, and fixtures.
- [ ] Define a single authoritative version source and make `VERSION`, package `__version__`, build metadata, and release tags derive from or validate against it.
- [ ] Configure deterministic build behavior: normalized timestamps where feasible, no local absolute paths, no untracked generated files, and stable package inclusion rules.
- [ ] Add build commands for wheel and sdist plus a clean-install smoke test into an empty virtual environment.
- [ ] Add package metadata validation (`twine check` or equivalent) and archive-content tests ensuring no credentials, caches, test debris, or unintended files ship.

### Verification and negative-test checklist

- [ ] Build wheel and sdist twice from the same commit/environment and compare manifests and, where reproducible-build policy requires it, hashes.
- [ ] Install each artifact into a clean environment and run import, version, schema-resource, and core-test smoke checks.
- [ ] Verify unsupported Python versions are rejected cleanly and supported versions are covered by CI.

### Required evidence/artifacts

- [ ] `pyproject.toml` and build configuration.
- [ ] Wheel/sdist artifact manifest and clean-install test log.
- [ ] Version-consistency report across source, metadata, and tag.

### Exit criterion

- [ ] **DONE only when:** A clean checkout can produce installable artifacts with explicit Python/dependency constraints, and those artifacts pass isolated install and smoke tests.

---

## MC-04 — Dependency lock/provenance

**Priority:** P0 — supply-chain blocker  
**Related INV-22 controls:** C031, C045, C050, C094, C100  

**Target state:** Make every build/test/runtime dependency resolvable to a known immutable artifact with integrity and origin evidence.

### Implementation checklist

- [ ] Select a lock mechanism appropriate to the packaging workflow and commit lock data for all production and CI dependency sets.
- [ ] Record exact versions plus cryptographic hashes for downloadable artifacts; disallow silent hash bypasses and unpinned VCS dependencies.
- [ ] For VCS dependencies, record canonical repository URL and immutable commit SHA; reject moving branches/tags unless the resolver verifies the resolved commit.
- [ ] Define trusted package indexes/registries and prohibit dependency confusion by explicitly controlling index precedence and internal package namespaces.
- [ ] Capture dependency origin/provenance metadata sufficient to trace each installed package to its source distribution or wheel.
- [ ] Add automated lock freshness and drift checks that fail when `pyproject.toml`/dependency inputs change without regenerating the lock.
- [ ] Establish an allow/deny policy for yanked, unsigned, vulnerable, or unsupported dependencies and a documented exception process.
- [ ] Generate a dependency inventory consumable by SBOM/vulnerability tooling and include it in release evidence.

### Verification and negative-test checklist

- [ ] Recreate the environment from the lock on a clean machine with network access restricted to approved registries.
- [ ] Tamper with a cached dependency artifact and verify hash/integrity checks reject installation.
- [ ] Change a declared dependency without refreshing the lock and verify CI blocks the change.

### Required evidence/artifacts

- [ ] Committed lockfile(s) with hashes.
- [ ] Dependency provenance/inventory artifact.
- [ ] CI integrity-check and dependency-drift results.

### Exit criterion

- [ ] **DONE only when:** Release dependencies resolve exclusively from approved sources to immutable, integrity-checked artifacts and environment recreation is deterministic.

---

## MC-05 — Actual WASIX/WASI implementation pin

**Priority:** P0 — semantic baseline blocker  
**Related INV-22 controls:** C010, C011, C016, C027, C031, C084, C093, C100  

**Target state:** Define exactly which standards-track WASI and alternative/WASIX specifications, interface packages, runtime implementations, and feature profiles the compatibility matrix compares.

### Implementation checklist

- [ ] Create a `baselines/` manifest that identifies the standards branch and fork branch by specification release, repository URL, commit/tag, and content digest.
- [ ] Pin each imported WIT/package definition by namespace/package/version and digest; do not rely on “latest” registries or mutable Git references.
- [ ] Enumerate the enabled WASIX feature profile relevant to this component (for example processes/subprocesses, networking, threads, fork-like behavior, filesystem extensions) instead of treating WASIX as one undifferentiated target.
- [ ] Record the concrete runtime implementations and versions used for reference conformance tests, while keeping the semantic matrix defined against contracts rather than a single runtime quirk.
- [ ] Document normalization rules for naming equivalent interfaces across branches and how moved/renamed packages are tracked.
- [ ] Store the source artifacts or verifiable fetch metadata needed to reconstruct the compared definitions offline.
- [ ] Require baseline updates to regenerate semantic diffs, fixtures, drift counts, and certification compatibility before merge.
- [ ] Add a release policy specifying how long older WASI/WASIX baselines remain supported and how incompatible baseline changes trigger schema/version changes.

### Verification and negative-test checklist

- [ ] Fetch/reconstruct both baselines from the manifest and verify all digests before analysis.
- [ ] Run the interface inventory/diff pipeline against the pinned baselines and prove the result is deterministic.
- [ ] Attempt to substitute a newer/unapproved runtime or spec revision and verify certification reports it as unsupported rather than silently accepting it.

### Required evidence/artifacts

- [ ] Baseline manifest with immutable identifiers and digests.
- [ ] Captured WIT/interface inventory for both branches.
- [ ] CI report linking matrix generation/certification to exact baseline revisions.

### Exit criterion

- [ ] **DONE only when:** Every classification can be traced to two exact branch baselines and reproduced from immutable source/specification inputs.

---

## MC-06 — Machine-readable branch matrix schema (`PK_BRANCH_MATRIX/1`)

**Priority:** P0 — public-contract blocker  
**Related INV-22 controls:** C004, C016, C021, C022, C026, C027, C029, C082, C100  

**Target state:** Define a versioned external schema and canonical serialization for the compatibility matrix so other components can validate and consume it without importing Python internals.

### Implementation checklist

- [ ] Specify a top-level envelope including contract identifier/version, matrix revision, source and target baseline identities, generation time, producer identity, entries, and integrity metadata.
- [ ] Define each entry with canonical interface ID, source package/version, target package/version, classification enum (`identical`, `shimmable`, `divergent`), rationale/reference, shim identifier when applicable, and deprecation metadata if present.
- [ ] Choose and document the normative schema technology (for example JSON Schema plus canonical JSON, WIT record types, or another project-approved IDL) and commit the schema under version control.
- [ ] Define canonical ordering/serialization so matrix digests are stable; reject duplicate interface IDs, unknown enum values, ambiguous normalization, and missing baseline identities.
- [ ] Specify schema evolution rules: additive-compatible fields, required major-version changes, unknown-field handling, and migration expectations.
- [ ] Define hard size/count limits and validation complexity limits to prevent resource-exhaustion attacks from malicious matrices.
- [ ] Add parser/validator APIs returning the structured error model rather than raw library exceptions.
- [ ] Publish valid, minimal, maximal, malformed, forward-version, duplicate-entry, and tampered fixtures.

### Verification and negative-test checklist

- [ ] Validate all fixtures against the schema and ensure invalid cases fail with stable error codes.
- [ ] Round-trip serialize/parse and verify canonical bytes and digest are stable.
- [ ] Cross-validate with an implementation independent of the primary Python parser or at least a schema-engine validation job.

### Required evidence/artifacts

- [ ] Versioned `PK_BRANCH_MATRIX/1` schema.
- [ ] Fixture corpus with expected verdicts.
- [ ] Canonicalization and schema-compatibility test results.

### Exit criterion

- [ ] **DONE only when:** A consumer can validate, hash, parse, and version-negotiate a matrix using only the published contract, and invalid/unknown data fails closed.

---

## MC-07 — Machine-readable shim contract (`PK_BRANCH_SHIM/1`)

**Priority:** P0 — public-contract blocker  
**Related INV-22 controls:** C021, C022, C025, C026, C027, C028, C029, C082, C100  

**Target state:** Replace the current ad-hoc metadata dictionary with a typed, versioned translation request/response contract that preserves provenance and cannot conceal loss.

### Implementation checklist

- [ ] Define request fields for contract version, interface ID/version, source branch/baseline, destination branch/baseline, operation/function, payload encoding, correlation ID, and optional deadline/cancellation context.
- [ ] Define response fields for translation status, output payload/encoding, applied shim implementation/version, source/destination schema digests, losslessness declaration, warnings, and diagnostic reference.
- [ ] Define an error union for unclassified interface, divergent semantics, unsupported direction/version, invalid payload, deadline exceeded, cancelled, policy denied, and internal translation failure.
- [ ] Specify maximum request/response sizes, recursion/container limits, streaming behavior, and whether partial outputs are ever legal (default should be no for semantic transformations).
- [ ] Define canonical payload encoding or explicitly bind payloads to interface-specific WIT/ABI schemas so arbitrary Python objects cannot cross the external boundary.
- [ ] Specify idempotency and replay rules for translation requests and distinguish pure translation from any side-effecting runtime operation.
- [ ] Version the shim implementation independently from the interface and record both in every result for reproducibility.
- [ ] Publish fixtures for both directions, identical pass-through, shimmable transforms, divergent refusal, unknown interface, malformed payload, and unsupported schema version.

### Verification and negative-test checklist

- [ ] Contract-test the same fixture corpus through every supported transport/API binding.
- [ ] Verify every successful cross-branch response identifies the exact shim and baselines used.
- [ ] Prove divergent and unclassified requests never produce an output payload.
- [ ] Fuzz length fields, nested payloads, enum values, and version fields for parser safety and deterministic error handling.

### Required evidence/artifacts

- [ ] Versioned `PK_BRANCH_SHIM/1` schema and error definitions.
- [ ] Bidirectional conformance fixtures and expected outputs.
- [ ] Contract/fuzz test reports.

### Exit criterion

- [ ] **DONE only when:** Translation is externally typed, bounded, provenance-rich, versioned, and fail-closed; the generic Python dictionary envelope is no longer the contract.

---

## MC-08 — Machine-readable certification contract (`PK_BRANCH_CERT/1`)

**Priority:** P0 — trust blocker  
**Related INV-22 controls:** C021, C022, C026, C044, C045, C049, C082, C090, C100  

**Target state:** Define a portable branch-certification record that binds a component artifact to the exact branch/matrix/baseline evidence under which it passed.

### Implementation checklist

- [ ] Define required fields: certificate schema/version, certificate ID, component identity/version, artifact digest(s), certified branch, baseline IDs, matrix digest/revision, test/evidence digest, issuer identity/key ID, issue time, validity window, and status.
- [ ] Include optional-but-structured fields for environment constraints, supported architectures/runtimes, exceptions/waivers, and certification scope; do not encode these as free-form prose only.
- [ ] Define canonical serialization and signing envelope so signature verification is deterministic across implementations.
- [ ] Define status semantics for valid, expired, revoked, superseded, suspended, and unknown; runtime enforcement must treat non-valid states as uncertified.
- [ ] Define revocation reference/sequence semantics and how consumers discover freshness when online and behave when offline.
- [ ] Specify certificate chaining or issuer trust requirements if subordinate issuers are allowed; otherwise explicitly prohibit them.
- [ ] Define schema evolution and version-negotiation rules and prohibit silent reinterpretation of old certificate fields.
- [ ] Publish positive and negative fixtures including digest mismatch, wrong branch, expired certificate, unknown issuer, revoked certificate, malformed signature, and unsupported version.

### Verification and negative-test checklist

- [ ] Validate and verify signed fixtures using an independent verifier path.
- [ ] Change one byte of the component, matrix, or evidence digest and prove verification fails.
- [ ] Exercise expiration/revocation/supersession and offline-staleness behavior at boundary times.

### Required evidence/artifacts

- [ ] Versioned `PK_BRANCH_CERT/1` schema.
- [ ] Canonical signed fixture set and trust-store fixture.
- [ ] Verification/revocation test evidence.

### Exit criterion

- [ ] **DONE only when:** A certification is a verifiable signed artifact with explicit scope, freshness, revocation, and cryptographic binding to the certified component and compatibility baseline.

---

## MC-09 — Persistent certification store

**Priority:** P0 — runtime enforcement blocker  
**Related INV-22 controls:** C032, C036, C037, C047, C049, C057, C095, C100  

**Target state:** Persist certifications durably with atomic issuance/revocation, indexed lookup, history, and recovery semantics instead of an in-memory dataclass only.

### Implementation checklist

- [ ] Define a storage port/interface separating certification semantics from backend implementation; include `issue`, `get`, `list`, `revoke`, `supersede`, and history/audit queries.
- [ ] Choose a reference backend suitable for local operation (for example transactional SQLite) and define the production backend requirements for multi-node use if needed.
- [ ] Design a schema keyed by certificate ID and component artifact digest; index branch, component, issuer, validity, and status for deterministic enforcement lookups.
- [ ] Use transactions/compare-and-swap semantics so issuance, revocation, and supersession cannot partially apply or race into contradictory active states.
- [ ] Store the signed certificate bytes plus parsed index fields; never reconstruct the signed object from mutable database columns during verification.
- [ ] Define retention and tombstone rules so revoked/superseded certifications remain auditable and cannot be silently resurrected.
- [ ] Encrypt sensitive stored metadata as required, enforce least-privilege database access, and separate read-only verifier access from issuer/revoker privileges.
- [ ] Implement backup/restore and corruption detection; include schema versioning and migration hooks from the first durable format.

### Verification and negative-test checklist

- [ ] Restart the process and prove issued/revoked status survives with identical signed bytes.
- [ ] Run concurrent issuance/revocation races and verify invariants (at most one active successor chain where policy requires it).
- [ ] Corrupt a record/index and verify integrity checking prevents trusting the record.
- [ ] Restore from backup and compare certificate set, statuses, and audit sequence to the source store.

### Required evidence/artifacts

- [ ] Storage schema/migration files and backend interface contract.
- [ ] Persistence/concurrency/recovery test reports.
- [ ] Backup/restore evidence and data-integrity checks.

### Exit criterion

- [ ] **DONE only when:** Certification state survives restart/failover, status transitions are atomic and auditable, and enforcement never trusts an unsigned/reconstructed or stale record.

---

## MC-10 — Cryptographic certification integrity

**Priority:** P0 — security blocker  
**Related INV-22 controls:** C044, C045, C047, C048, C049, C050, C090, C100  

**Target state:** Protect certification authenticity and artifact binding with managed cryptographic signing, verification, key lifecycle, and replay/tamper defenses.

### Implementation checklist

- [ ] Define the approved signature algorithm/profile and canonical signing envelope; prohibit ad-hoc cryptography and ambiguous serialization.
- [ ] Bind signatures to certificate schema/version, certificate ID, component artifact digest, branch, baseline/matrix digest, evidence digest, issuer, and validity timestamps.
- [ ] Create a trust-store model with key IDs, issuer identities, allowed signing purposes, activation/retirement times, and revocation state.
- [ ] Separate issuer private-key access from ordinary verifier/runtime processes; use a managed signing service/HSM/KMS where required by the deployment threat model.
- [ ] Implement key rotation with overlapping verification windows, explicit successor keys, and no need to re-sign still-valid historical records unless policy requires it.
- [ ] Define clock-skew tolerance and safe failure when trusted time is unavailable; prevent an unavailable time service from silently extending expired credentials.
- [ ] Protect against replay of revoked/superseded certificates using revocation sequence/epoch or freshness metadata and cache-age limits.
- [ ] Log signing, verification failure, revocation, key change, and trust-store update events to the tamper-evident audit channel without exposing private material.

### Verification and negative-test checklist

- [ ] Verify known-good signatures and reject altered payload, signature, issuer, key ID, digest, and timestamp fields.
- [ ] Exercise active-to-retired key rotation and confirm old valid signatures remain/verifiably cease according to policy.
- [ ] Test stale revocation cache, unavailable key service, unavailable time source, and unknown issuer behavior; all security-critical uncertainty must fail closed.
- [ ] Run cryptographic test vectors and interoperability verification using a second implementation/library where practical.

### Required evidence/artifacts

- [ ] Signing profile/trust policy and key lifecycle document.
- [ ] Signed certification vectors and verification test results.
- [ ] Key rotation/revocation drill evidence.

### Exit criterion

- [ ] **DONE only when:** Certification authenticity and integrity can be independently verified, artifact/evidence substitution is impossible without detection, and key compromise/rotation has a documented tested response.

---

## MC-11 — Complete interface inventory discovery

**Priority:** P0 — matrix-completeness blocker  
**Related INV-22 controls:** C004, C011, C020, C021, C029, C031, C083, C100  

**Target state:** Prove that every WASI/WASIX interface actually in use is represented in the matrix instead of relying on the current five hard-coded names.

### Implementation checklist

- [ ] Define authoritative discovery sources: pinned WIT/package manifests, component import sections, runtime capability manifests, deployment manifests, and any generated bindings used by supported workloads.
- [ ] Implement parsers that normalize package/interface/function identifiers into one canonical namespace including version information.
- [ ] Build an inventory command that emits all discovered interfaces with origin file/package, branch, version, and usage/reference path.
- [ ] Reconcile discovered standards and fork inventories and mark every interface as classified, intentionally ignored with justification, or unsupported; unknown must block certification.
- [ ] Detect aliases/renames explicitly rather than treating name equality as semantic equality; maintain a reviewed alias mapping.
- [ ] Track interface reachability from real supported workloads so unused definitions can be distinguished from interfaces required in production.
- [ ] Generate a machine-readable completeness report showing discovered count, classified count, excluded count, and unclassified count.
- [ ] Make completeness a release gate with zero unclassified interfaces for any supported workload profile.

### Verification and negative-test checklist

- [ ] Add a new WIT/interface import to a fixture workload and verify the gate fails until the interface is classified.
- [ ] Remove/rename an interface and verify inventory drift is detected rather than silently disappearing.
- [ ] Cross-check static discovery against runtime instrumentation/capability reports for representative workloads.

### Required evidence/artifacts

- [ ] Canonical interface inventory artifact.
- [ ] Inventory-to-matrix completeness report.
- [ ] Workload reachability fixtures and CI gate result.

### Exit criterion

- [ ] **DONE only when:** For every supported workload, all referenced interfaces are discoverable and either explicitly classified or explicitly unsupported; unclassified count is zero at certification.

---

## MC-12 — Automatic matrix generation/diffing

**Priority:** P1 — correctness automation  
**Related INV-22 controls:** C004, C016, C020, C029, C031, C083, C093  

**Target state:** Generate reviewable compatibility candidates and semantic diffs from pinned branch definitions, while preserving human approval for semantic classification.

### Implementation checklist

- [ ] Parse both pinned interface-definition sets into a normalized abstract model covering packages, interfaces, functions, types, resources, flags/enums, errors, async/streaming semantics, and documentation annotations relevant to semantics.
- [ ] Implement structural diffing for additions/removals, renamed items, parameter/result changes, type width/signedness, ownership/resource changes, error-set changes, and capability differences.
- [ ] Classify only provably identical definitions automatically; emit all other changes as `needs_review` rather than guessing `shimmable` or `divergent`.
- [ ] Produce a deterministic candidate matrix and a detailed per-interface diff artifact with source locations and baseline digests.
- [ ] Support a reviewed override file carrying classification rationale, reviewer, approval date, linked proof/test, and expiration/review trigger.
- [ ] Fail generation on parser ambiguity, duplicate canonical identifiers, unsupported syntax, or baseline digest mismatch.
- [ ] Make the generator output stable across runs and sort entries canonically for review/digesting.
- [ ] Integrate the generator into CI so hand-edited matrix changes that do not correspond to source definitions or reviewed overrides are rejected.

### Verification and negative-test checklist

- [ ] Use synthetic WIT fixtures covering every structural change category and assert the expected diff.
- [ ] Run generation twice from identical inputs and verify byte-for-byte canonical output.
- [ ] Inject a semantic change with no override and verify the release gate remains blocked.

### Required evidence/artifacts

- [ ] Normalized interface AST/model format.
- [ ] Generated semantic diff and candidate matrix.
- [ ] Approved override records and generator regression suite.

### Exit criterion

- [ ] **DONE only when:** The matrix is derivable from immutable branch definitions plus explicit reviewed semantic decisions; unexplained manual drift cannot enter a release.

---

## MC-13 — Semantic compatibility proof mechanism

**Priority:** P0 — correctness blocker  
**Related INV-22 controls:** C011, C020, C029, C030, C041, C050, C081–C090, C100  

**Target state:** Replace manually asserted `SHIMMABLE` labels with documented proof obligations and executable evidence that translation preserves observable semantics.

### Implementation checklist

- [ ] Define formal classification criteria: `identical` requires schema/ABI and behavioral equivalence within the supported profile; `shimmable` requires a total lossless mapping for allowed inputs; `divergent` covers any non-preservable semantics.
- [ ] For each shimmable interface, specify invariants over inputs, outputs, errors, ordering, resource lifetimes, side effects, capabilities, concurrency, and determinism.
- [ ] Define a proof artifact format linking interface/baseline versions to translator implementation, property tests, differential traces, known exclusions, and reviewer approval.
- [ ] Use type-level/ABI comparison to prove representation compatibility where possible and property/differential testing where behavior matters.
- [ ] Require explicit treatment of errno/error mapping, path/descriptor rights, resource ownership, blocking/async behavior, and security/capability semantics; a lossy or privilege-expanding mapping must be classified divergent.
- [ ] Define the supported input domain; if the translator is only partial, encode preconditions in policy and reject inputs outside them rather than silently narrowing.
- [ ] Invalidate/review proofs automatically when either baseline schema, translator code, policy, or relevant runtime version changes.
- [ ] Require two-person review (or project-equivalent approval) for transitions from divergent/unclassified to shimmable/identical.

### Verification and negative-test checklist

- [ ] Property-test round-trip and observational invariants across generated valid inputs.
- [ ] Differentially execute representative operations on both branches and compare normalized externally observable results.
- [ ] Seed known non-equivalent cases and verify the proof system refuses `SHIMMABLE` classification.
- [ ] Mutation-test translators/proof predicates to ensure tests detect intentional semantic corruption.

### Required evidence/artifacts

- [ ] Per-interface semantic proof records.
- [ ] Property/differential test corpus and results.
- [ ] Review/approval metadata tied to baseline and translator digests.

### Exit criterion

- [ ] **DONE only when:** No interface is labeled `SHIMMABLE` without version-bound executable evidence demonstrating the defined semantic invariants and zero unacknowledged information/capability loss.

---

## MC-14 — Real bidirectional translators

**Priority:** P0 — functional blocker  
**Related INV-22 controls:** C011, C021, C022, C025, C026, C029, C030, C081–C090, C100  

**Target state:** Implement actual standards→fork and fork→standards conversions for every approved shimmable interface using the real typed WASI/WASIX data model, not a metadata wrapper.

### Implementation checklist

- [ ] Create a translator registry keyed by canonical interface ID, source schema version, destination schema version, and direction; refuse missing or ambiguous registrations.
- [ ] Implement typed conversion functions at the schema/WIT boundary, including nested records, variants, handles/resources, flags, errors, streams, and ownership semantics as applicable.
- [ ] Keep translators pure where semantics permit; separate any environment-dependent lookup/side effect behind explicit injected capabilities.
- [ ] Perform range/encoding/normalization checks before conversion and return structured errors for non-representable values; never truncate, coerce, or drop fields silently.
- [ ] Preserve security-relevant rights/capabilities monotonically: translation must not grant filesystem/network/process authority absent from the source request.
- [ ] Handle resource lifetime and handle identity explicitly so a translation cannot create stale/double-owned handles or leak resources.
- [ ] Version translators independently and include implementation digest/version in results/certification evidence.
- [ ] Implement both directions separately unless a mechanically proven inverse can be generated; do not assume reversing one mapping is correct.
- [ ] Provide interface-specific golden vectors generated from pinned branch definitions and real runtime observations.

### Verification and negative-test checklist

- [ ] Run bidirectional golden tests for boundary values, empty/maximal structures, all enum/variant cases, errors, and resource-lifetime scenarios.
- [ ] Run round-trip properties where the mapping is bijective and explicit canonicalization properties where multiple representations normalize to one.
- [ ] Differentially validate translator outputs against project-approved WASI/WASIX runtimes.
- [ ] Test privilege non-escalation and rejection of non-representable values.

### Required evidence/artifacts

- [ ] Translator implementation registry and version manifest.
- [ ] Golden vectors and round-trip/differential reports.
- [ ] Security review demonstrating no capability amplification.

### Exit criterion

- [ ] **DONE only when:** Every `SHIMMABLE` classification has executable, versioned translators in both required directions that pass semantic proof and runtime differential tests.

---

## MC-15 — Shim round-trip validation

**Priority:** P0 — correctness gate  
**Related INV-22 controls:** C029, C030, C081, C082, C085, C088, C090, C100  

**Target state:** Systematically prove translation reversibility or documented canonical equivalence across the entire supported input domain.

### Implementation checklist

- [ ] Define per-interface round-trip properties `decode(encode(x)) == x` or an explicit semantic-equivalence relation when canonicalization is permitted.
- [ ] Generate property-based inputs from the exact WIT/schema constraints, including boundary integer values, Unicode/path edge cases, empty/maximal collections, invalid encodings, and resource-state transitions.
- [ ] Add a corpus of historically problematic and adversarial values to prevent regressions hidden by random generation.
- [ ] Check both directions independently and detect information loss by comparing normalized field/rights/error sets before and after translation.
- [ ] Track and enforce deterministic serialization for translated values so repeated translation cannot accumulate drift.
- [ ] Set iteration counts/seeds suitable for CI plus deeper scheduled/nightly runs and persist failing seeds as regression fixtures.
- [ ] Measure translator coverage and ensure every branch/variant/error arm is exercised by round-trip or negative tests.
- [ ] Block certification when a translator lacks a passing round-trip/canonical-equivalence proof for the pinned version pair.

### Verification and negative-test checklist

- [ ] Mutation-test field drops, enum remaps, rights widening, sign/width changes, and error-code substitutions; the property suite must catch each mutation.
- [ ] Run large randomized suites under sanitizers/runtime checks where implementation language permits.
- [ ] Re-run all persisted counterexamples on every release.

### Required evidence/artifacts

- [ ] Property definitions and generator strategies.
- [ ] Seed/counterexample corpus.
- [ ] Per-interface round-trip coverage and result report.

### Exit criterion

- [ ] **DONE only when:** All supported translator domains satisfy the documented inverse/equivalence properties, with failing seeds retained and certification blocked on any regression.

---

## MC-16 — Structured production error model

**Priority:** P0 — API contract blocker  
**Related INV-22 controls:** C014, C022, C025, C026, C029, C071, C073, C076, C082  

**Target state:** Expose stable machine-readable failure semantics across library/CLI/API boundaries instead of leaking Python exception class/text behavior.

### Implementation checklist

- [ ] Define a namespaced error-code enum covering validation, classification, translation, certification, authentication/authorization, dependency, timeout/cancel, resource limit, storage, integrity, and internal failures.
- [ ] For each code, define retryability, HTTP/RPC/CLI mapping if applicable, security disclosure level, operator action, and whether it is terminal for certification.
- [ ] Define a structured error object containing code, category, safe message, correlation/trace ID, relevant resource/interface IDs, and optional bounded details; exclude secrets and untrusted raw payloads.
- [ ] Map existing `Unclassified`, `InvalidClassification`, `SemanticDivergence`, and `UncertifiedBranch` exceptions into stable external codes while preserving internal stack traces only in protected diagnostics.
- [ ] Define nested/cause semantics for dependency failures without allowing arbitrary exception serialization.
- [ ] Version error codes additively and never repurpose an existing code for a different meaning.
- [ ] Document which errors count toward SLOs/alerts and which represent expected policy refusals.
- [ ] Provide language-neutral schema/fixtures so adjacent components can parse errors without Python coupling.

### Verification and negative-test checklist

- [ ] Contract-test every public operation for each documented error family and verify stable code/detail shape.
- [ ] Fuzz invalid inputs and confirm callers receive bounded structured errors rather than crashes or traceback leakage.
- [ ] Snapshot-test error redaction and ensure secrets/path internals are not exposed in ordinary responses/logs.

### Required evidence/artifacts

- [ ] Versioned error schema and code registry.
- [ ] Error-to-retry/SLO/operator-action matrix.
- [ ] Contract/redaction test fixtures.

### Exit criterion

- [ ] **DONE only when:** All externally observable failures have stable documented codes and safe structured details; raw Python exceptions are implementation details only.

---

## MC-17 — Timeout/cancellation/backpressure semantics

**Priority:** P1 — interface resilience  
**Related INV-22 controls:** C014, C025, C028, C053, C054, C067, C082, C088  

**Target state:** Define bounded execution behavior for translation, certification, storage, and dependency calls so slow or overloaded operations cannot hang callers or create unbounded work.

### Implementation checklist

- [ ] Classify each public operation as synchronous/fast, potentially blocking, asynchronous, or streaming and assign a default/max deadline budget.
- [ ] Propagate caller deadlines through dependency/storage/translator layers and stop initiating downstream work when the remaining budget is insufficient.
- [ ] Define cooperative cancellation semantics and cleanup requirements for partially allocated resources, temporary files, handles, locks, and transactions.
- [ ] Mark which operations are safe to retry and define idempotency keys or naturally idempotent identifiers for state-changing calls such as certification issuance/revocation.
- [ ] Implement bounded queues/semaphores around expensive translation/certification work; reject or shed excess work with a structured overload code rather than unbounded memory growth.
- [ ] Define per-interface backpressure for streaming/large payloads and a maximum buffered byte/item count.
- [ ] Use bounded exponential backoff with jitter only for transient, retry-safe dependency errors and cap total retry time by the original deadline.
- [ ] Expose timeout, cancellation, queue rejection, and retry metrics tagged by operation/interface while controlling cardinality.

### Verification and negative-test checklist

- [ ] Inject a stalled dependency and prove operations terminate within the configured deadline plus a documented tolerance.
- [ ] Cancel operations at multiple execution points and verify no leaked locks, transactions, resources, or partial certificates remain.
- [ ] Load beyond queue/concurrency limits and verify bounded memory, deterministic overload errors, and recovery after load subsides.

### Required evidence/artifacts

- [ ] Operation deadline/retry/idempotency matrix.
- [ ] Load/cancellation test results and leak checks.
- [ ] Telemetry showing bounded queues and timeout behavior.

### Exit criterion

- [ ] **DONE only when:** Every potentially blocking operation has explicit deadline, cancellation, retry, idempotency, and overload behavior that is exercised under failure/load tests.

---

## MC-18 — Authentication boundary implementation

**Priority:** P0 — security blocker  
**Related INV-22 controls:** C023, C041, C044, C047, C048, C050, C100  

**Target state:** Authenticate every actor that can read or mutate compatibility, translation, policy, or certification state before granting trust.

### Implementation checklist

- [ ] Enumerate trust boundaries and actor classes: local operator, control plane, workload/component, CI/release issuer, storage service, adjacent architecture service, and automated verifier.
- [ ] Select deployment-appropriate authentication mechanisms for each boundary (for example workload identity/mTLS for services and signed/OIDC-backed identity for operators) and explicitly document unsupported mechanisms.
- [ ] Bind authenticated identity to the transport/session and propagate a stable principal identifier into authorization, audit, and telemetry.
- [ ] Validate issuer, audience, signature, expiry/not-before, subject, and required claims for tokens/certificates; never accept unsigned or algorithm-confused credentials.
- [ ] Define bootstrap trust roots and rotation procedures; separate trust for human operators, services, and artifact/certification issuers.
- [ ] Implement replay protection/session freshness where the chosen mechanism requires it and enforce TLS/channel-binding policy for remote interfaces.
- [ ] Fail closed when authentication or trust-root validation is unavailable; define narrowly scoped read-only degraded behavior only if explicitly approved.
- [ ] Redact credentials from errors, logs, traces, crash reports, fixtures, and test snapshots.

### Verification and negative-test checklist

- [ ] Test valid/expired/not-yet-valid/wrong-audience/wrong-issuer/revoked/unknown-key credentials.
- [ ] Attempt anonymous calls to every protected operation and verify deterministic authentication failure before business logic executes.
- [ ] Exercise key/certificate rotation and temporary identity-provider unavailability.
- [ ] Run replay/spoofing tests appropriate to the selected credential type.

### Required evidence/artifacts

- [ ] Authentication architecture and trust-root inventory.
- [ ] Boundary-by-boundary authentication test matrix.
- [ ] Rotation/outage drill results.

### Exit criterion

- [ ] **DONE only when:** Every externally invokable privileged boundary has verified principal identity, tested credential lifecycle handling, and no anonymous fallback.

---

## MC-19 — Authorization/capability enforcement

**Priority:** P0 — security blocker  
**Related INV-22 controls:** C024, C041–C043, C046, C048–C050, C100  

**Target state:** Enforce least-privilege permissions for reading matrices, translating payloads, changing classifications/policy, and issuing/revoking certifications.

### Implementation checklist

- [ ] Define an action/resource model such as `matrix.read`, `matrix.publish`, `translation.execute`, `cert.issue`, `cert.revoke`, `policy.admin`, `audit.read`, and `config.activate`.
- [ ] Map authenticated principals/roles/workload identities to explicit capabilities; default-deny any action without a matching grant.
- [ ] Separate duties so one identity cannot both alter compatibility policy and self-issue production certification without the project-approved approval path.
- [ ] Scope permissions by environment/site/component/branch where applicable and prevent wildcard authority from leaking across tenant/workload boundaries.
- [ ] Apply authorization checks at the authoritative operation boundary, not only in CLI/UI wrappers; internal APIs must not bypass policy.
- [ ] Represent capabilities in machine-readable policy/config with version, provenance, approval, and activation time.
- [ ] Define break-glass access with strong authentication, short expiry, explicit reason, enhanced audit, and post-event review rather than hidden administrator bypasses.
- [ ] Validate downstream capability monotonicity: shims and translated calls must never result in broader filesystem/network/process rights than the source request/certificate permits.

### Verification and negative-test checklist

- [ ] Create a principal×action authorization matrix and contract-test every allow/deny cell relevant to production roles.
- [ ] Test privilege escalation attempts using resource-ID substitution, environment crossing, wildcard scopes, stale roles, and confused-deputy call chains.
- [ ] Test break-glass expiry/revocation and prove all such actions are auditable.

### Required evidence/artifacts

- [ ] Versioned authorization policy/schema and role/capability matrix.
- [ ] Positive/negative authorization test report.
- [ ] Separation-of-duties and break-glass audit evidence.

### Exit criterion

- [ ] **DONE only when:** All privileged operations are default-deny and capability-scoped at the authoritative boundary, with tested separation of duties and no implicit ambient authority.

---

## MC-20 — Configuration subsystem

**Priority:** P1 — operability foundation  
**Related INV-22 controls:** C032–C036, C039, C071, C100  

**Target state:** Provide typed declarative configuration with secure defaults and a clean separation between immutable artifacts, mutable configuration, secrets, and runtime state.

### Implementation checklist

- [ ] Define a versioned configuration schema covering branch baseline selection, matrix/cert stores, policy references, limits, telemetry, networking/listening, and approved feature flags.
- [ ] Choose one canonical configuration format and define environment-variable/CLI overrides with deterministic precedence; prohibit uncontrolled “magic” settings.
- [ ] Separate secrets by reference (secret URI/key name/credential provider) rather than embedding secret values in ordinary configuration.
- [ ] Make defaults explicit and security-conservative: no wildcard listener, anonymous mutation, unbounded queues, unsigned certificates, or auto-classification of unknown interfaces.
- [ ] Implement a typed loader that rejects unknown critical fields, invalid enums, duplicate keys, wrong types, unsafe paths/URLs, and out-of-range resource limits.
- [ ] Expose a sanitized effective-configuration view that identifies source/provenance of each setting without revealing secrets.
- [ ] Support environment/site overlays without rebuilding the package while preserving immutable baseline/schema artifacts.
- [ ] Document configuration compatibility/version migration rules and supported override precedence.

### Verification and negative-test checklist

- [ ] Parse minimal/default, complete, boundary-value, unknown-field, malformed, and unsafe configuration fixtures.
- [ ] Verify secrets never appear in the effective-config output or logs.
- [ ] Verify environment/site overlays change only allowed mutable settings and cannot mutate immutable baselines/schemas.

### Required evidence/artifacts

- [ ] Configuration schema and secure-default reference file.
- [ ] Precedence/provenance documentation.
- [ ] Configuration parser/redaction test suite.

### Exit criterion

- [ ] **DONE only when:** A clean deployment can be configured declaratively and safely, with deterministic precedence, typed validation, secret indirection, and a sanitized effective-config report.

---

## MC-21 — Configuration validation and atomic activation

**Priority:** P0 — safe-change blocker  
**Related INV-22 controls:** C034, C036–C038, C049, C059, C092, C100  

**Target state:** Ensure a configuration/policy/matrix change is fully validated before becoming active and can never leave the system in a partially applied state.

### Implementation checklist

- [ ] Implement a staged state model such as received → parsed → validated → authorized → prepared → committed/active, with rejected/rolled-back terminal paths.
- [ ] Validate syntax, schema, referenced files/digests, baseline compatibility, policy invariants, resource limits, trust roots, and dependency compatibility before activation.
- [ ] Compute an immutable configuration revision/digest and store author/principal, source, review/approval metadata, activation time, and previous revision.
- [ ] Use transactional/compare-and-swap activation so all readers observe either the old revision or the new revision, never mixed state.
- [ ] Perform pre-commit dry-run checks for matrix completeness, certification validity impact, and required translator availability.
- [ ] Persist the previous known-good revision and implement an atomic rollback path guarded by the same validation/authentication/audit controls.
- [ ] Invalidate or recalculate caches only after successful commit; prevent a failed update from mutating in-memory singleton state.
- [ ] Emit an audit event and metrics for validation failure, activation, rollback, and rejected stale revision attempts.

### Verification and negative-test checklist

- [ ] Inject failures at every activation stage and verify the prior revision remains active and durable.
- [ ] Run concurrent update races and prove stale writers cannot overwrite a newer revision.
- [ ] Restart during/after activation and prove recovery resolves to one complete valid revision.
- [ ] Attempt activation of a config that would make a currently certified workload unsafe and verify policy blocks or explicitly requires recertification.

### Required evidence/artifacts

- [ ] Configuration revision records and transactional state-machine tests.
- [ ] Fault-injection/restart consistency results.
- [ ] Audit entries linking actor, diff/digest, validation verdict, and activation/rollback.

### Exit criterion

- [ ] **DONE only when:** No invalid or partial configuration can become active; every activation is revisioned, attributable, atomic, recoverable, and rollback-tested.

---

## MC-22 — Secrets handling integration

**Priority:** P0 — security hygiene  
**Related INV-22 controls:** C039, C041, C043, C047–C050, C073, C075, C079, C100  

**Target state:** Keep credentials, signing keys, tokens, and sensitive endpoints out of source/configuration/telemetry and access them through narrow managed secret interfaces.

### Implementation checklist

- [ ] Inventory every secret class the component may need: issuer signing key reference, database credential, service credential, TLS private key, trust-store update credential, and external telemetry credential.
- [ ] Use secret-provider references/identity-based access rather than plaintext environment files where production infrastructure supports it; document development-only alternatives separately.
- [ ] Load secrets just-in-time where feasible, minimize lifetime in memory, and avoid global variables/string formatting/copying that unnecessarily duplicates material.
- [ ] Implement redaction utilities for logs/errors/config dumps and test key-name/value-pattern cases including nested structures.
- [ ] Separate public verification keys/trust bundles from private signing material and ensure ordinary runtime/verifier roles never receive issuer private keys.
- [ ] Define secret rotation/reload behavior and whether restart is required; avoid partial rotation where old/new dependencies become inconsistent.
- [ ] Ensure crash dumps, test fixtures, trace attributes, CLI history, and generated support bundles exclude secret content.
- [ ] Add repository/CI secret scanning and block known credential patterns or accidental private-key files.

### Verification and negative-test checklist

- [ ] Inject marker secrets and exercise all diagnostic paths; scan produced logs/traces/errors/config reports to confirm zero leakage.
- [ ] Rotate credentials while under load and verify service continuity or documented fail-closed behavior.
- [ ] Attempt access to signing/database secrets using read-only verifier identity and verify denial.

### Required evidence/artifacts

- [ ] Secret inventory and access matrix.
- [ ] Redaction/leak test results.
- [ ] Rotation procedure and drill evidence.

### Exit criterion

- [ ] **DONE only when:** No production secret is stored in normal repository/configuration artifacts or exposed through diagnostics, and access/rotation is least-privilege and tested.

---

## MC-23 — Runtime/site branch-selection control

**Priority:** P0 — invariant enforcement blocker  
**Related INV-22 controls:** C006, C011, C015, C019, C024, C032–C038, C058–C059, C071, C076–C078, C100  

**Target state:** Implement the contract invariant that a site has one authoritative active branch and a workload runs only when its certification is compatible with that site branch.

### Implementation checklist

- [ ] Define persisted desired and observed site branch state including branch, baseline version, revision, activation epoch/fencing token, actor, and timestamp.
- [ ] Provide an authorized control-plane operation to propose/validate/activate a branch change; never infer branch from the first workload or runtime discovered.
- [ ] Before activation, enumerate affected workloads/components and require valid certification for the target branch/baseline or block the transition.
- [ ] Use a monotonic revision/fencing token so stale controllers cannot reactivate an old branch after failover or partition.
- [ ] Enforce the active branch at workload admission/link/composition time via the INV-10 boundary and again at runtime entry where practical (defense in depth).
- [ ] Define transition states and drain/quiesce behavior if branch changes are allowed on a live site; explicitly prohibit mixed-branch operation unless a separately designed migration mode exists.
- [ ] Persist transition/audit history and expose desired/observed branch plus mismatch state via health/explain APIs.
- [ ] Add emergency freeze/disable controls that prevent new admissions without silently reclassifying/certifying workloads.

### Verification and negative-test checklist

- [ ] Attempt to run a standards-certified component on a fork site and vice versa; admission must fail before workload execution.
- [ ] Race two controllers proposing different branches and verify fencing guarantees a single active revision.
- [ ] Inject controller restart/partition during transition and verify no mixed or ambiguous active state is produced.

### Required evidence/artifacts

- [ ] Site-branch state schema and transition diagram.
- [ ] Admission/control-plane integration test report.
- [ ] Audit/explain output for a branch transition and a refused workload.

### Exit criterion

- [ ] **DONE only when:** A single authoritative site branch is durable and observable, stale writers are fenced, and uncertified workloads cannot be admitted on the active branch.

---

## MC-24 — Lifecycle/state machine

**Priority:** P1 — correctness/operations  
**Related INV-22 controls:** C014–C016, C034–C038, C057–C059, C071, C076, C092, C095, C099  

**Target state:** Define legal lifecycle states and transitions for matrices, shims, certifications, configuration revisions, and site branch activation.

### Implementation checklist

- [ ] Model matrix lifecycle states such as draft → validated → approved/published → active → deprecated → retired, with rejected/quarantined paths.
- [ ] Model certification states such as pending → issued/valid → suspended → revoked/expired/superseded and specify which states satisfy admission.
- [ ] Model configuration/branch transitions separately from certificate lifecycle so one state machine cannot accidentally imply another.
- [ ] Define transition preconditions, required actor/capability, side effects, idempotency, and emitted audit event for every edge.
- [ ] Reject illegal state jumps in the authoritative domain model/storage transaction rather than relying on UI workflow.
- [ ] Assign monotonic revision/sequence numbers and expected-state preconditions to prevent stale updates.
- [ ] Define restart/replay behavior for in-progress transitions and terminal handling for indeterminate external side effects.
- [ ] Expose current state, last transition reason/actor/time, and permitted next transitions through operator interfaces.

### Verification and negative-test checklist

- [ ] Exhaustively unit-test all legal transitions and representative illegal transitions for each state machine.
- [ ] Property-test that no transition path can make revoked/invalid artifacts active without revalidation.
- [ ] Crash/restart at transaction boundaries and verify state resolves deterministically.

### Required evidence/artifacts

- [ ] State-machine diagrams and machine-readable transition tables.
- [ ] Transition unit/property test report.
- [ ] Audit examples for approval, activation, suspension, revocation, and rollback.

### Exit criterion

- [ ] **DONE only when:** Lifecycle transitions are explicit, enforced, auditable, race-safe, and recoverable; no artifact becomes active through an undefined state change.

---

## MC-25 — Compatibility/version negotiation

**Priority:** P0 — interoperability blocker  
**Related INV-22 controls:** C016, C022, C027, C030, C084, C093, C100  

**Target state:** Negotiate supported `PK_BRANCH_*` contract/schema versions and branch baselines explicitly rather than assuming all peers speak version 1 identically.

### Implementation checklist

- [ ] Maintain a compatibility table for matrix/shim/cert schema major/minor versions, branch baselines, and adjacent component versions.
- [ ] Define negotiation inputs/outputs: locally supported versions, peer-supported versions, selected version, required features, and rejection reason when no safe intersection exists.
- [ ] Use major-version incompatibility as fail-closed; document whether minor versions are additive/backward-compatible and how unknown optional fields are handled.
- [ ] Negotiate before parsing semantic payloads where possible, or use a self-describing envelope that can safely reject unknown versions.
- [ ] Bind the negotiated version/baseline to request context and certification evidence so a mid-session downgrade cannot alter semantics invisibly.
- [ ] Protect negotiation against downgrade attacks by policy: prefer highest mutually approved version and optionally require a minimum security baseline.
- [ ] Define rolling-upgrade behavior for mixed service versions and the exact point at which older contracts stop being accepted.
- [ ] Expose selected/peer versions in diagnostics, traces, and dependency health without leaking sensitive identifiers.

### Verification and negative-test checklist

- [ ] Test every supported version pair plus unsupported future/old major versions.
- [ ] Attempt forced downgrade to a policy-disallowed version and verify rejection.
- [ ] Run rolling-upgrade integration tests with old/new peers and verify no ambiguous serialization/behavior.

### Required evidence/artifacts

- [ ] Machine-readable supported-version matrix.
- [ ] Negotiation fixtures and pairwise compatibility CI results.
- [ ] Rolling-upgrade compatibility evidence.

### Exit criterion

- [ ] **DONE only when:** Peers select an explicitly supported contract/baseline or fail with a stable incompatibility error; no version is assumed or silently downgraded.

---

## MC-26 — Resource and quota enforcement

**Priority:** P1 — availability/security  
**Related INV-22 controls:** C017, C028, C041, C050, C054, C061–C069, C088, C100  

**Target state:** Bound memory, CPU, concurrency, payload, queue, connection, and storage use so hostile or accidental load cannot destabilize the component or neighboring workloads.

### Implementation checklist

- [ ] Define hard payload/depth/count limits for matrices, certificates, translation inputs, fixture uploads, and diagnostic requests.
- [ ] Set per-operation concurrency limits and separate pools for expensive translation/diffing versus lightweight reads/health to avoid starvation.
- [ ] Define queue capacity, admission policy, fairness key, and overload response; prohibit unbounded queues.
- [ ] Set memory/buffer limits for parsing/serialization and stream large inputs where supported rather than buffering arbitrary documents.
- [ ] Define persistent-store quotas/retention for certificates, revisions, drift history, and audit records; reserve headroom for security-critical revocations/audit writes.
- [ ] Support site/environment/workload-specific quotas only where they cannot weaken global safety ceilings.
- [ ] Expose saturation signals such as active workers, queue utilization, rejected requests, storage utilization, and high-water marks.
- [ ] Define safe behavior at quota exhaustion, including which writes are rejected and how operators recover capacity without data corruption.

### Verification and negative-test checklist

- [ ] Send maximal and over-limit payloads/nesting/counts and confirm early bounded rejection.
- [ ] Load-test concurrency/queue saturation and verify memory remains within the documented envelope and low-cost health/read paths remain available as designed.
- [ ] Attempt one principal/workload to monopolize capacity and verify fairness/admission controls.

### Required evidence/artifacts

- [ ] Resource-limit specification and defaults.
- [ ] Load/saturation benchmark report with memory/CPU/queue graphs.
- [ ] Quota-exhaustion recovery test evidence.

### Exit criterion

- [ ] **DONE only when:** All externally influenced resource dimensions have tested hard limits and overload behavior; capacity exhaustion cannot create unbounded growth or bypass security-critical operations.

---

## MC-27 — Offline/intermittent-connectivity behavior

**Priority:** P1 — edge resilience  
**Related INV-22 controls:** C018, C027, C048, C051, C055–C058, C089, C095  

**Target state:** Define safe operation when control-plane, identity, revocation, baseline, or storage services are intermittently unavailable, especially for edge deployments.

### Implementation checklist

- [ ] Classify data by offline usability: immutable pinned baselines/schemas, cached trust roots, cached certifications, revocation/freshness state, configuration, and audit backlog.
- [ ] Define maximum staleness/lease duration for cached certification and policy data; after expiry, fail closed for new admissions rather than indefinitely trusting stale state.
- [ ] Persist enough validated state locally for explicitly approved read/admission operation during short outages, while prohibiting policy/classification/certification mutation without authoritative services.
- [ ] Queue only audit/telemetry records that can be durably buffered with bounded storage; define overflow behavior that preserves security-critical evidence or fails safe.
- [ ] Use monotonic sequence/revision metadata to reconcile remote changes after reconnect and detect conflicts instead of “last writer wins” by wall clock.
- [ ] Define identity/key/time-service outage behavior separately; do not infer successful authentication from cache when policy forbids it.
- [ ] Expose `offline`, `stale`, `degraded`, and `freshness_deadline` state to operators and admission logic.
- [ ] Document which capabilities are unavailable offline and the exact conditions required to resume normal mode after reconnect.

### Verification and negative-test checklist

- [ ] Partition each external dependency independently and in combinations; verify behavior matches the offline capability matrix.
- [ ] Advance simulated time beyond cache/lease limits and confirm stale credentials/certifications stop authorizing new activity.
- [ ] Reconnect after conflicting remote/local revisions and verify deterministic reconciliation/refusal rather than silent overwrite.

### Required evidence/artifacts

- [ ] Offline capability/staleness matrix.
- [ ] Partition/reconnect test results.
- [ ] Operator health/explain examples for fresh, degraded, stale, and recovered states.

### Exit criterion

- [ ] **DONE only when:** Offline operation is explicitly bounded by freshness and capability rules, reconnect reconciliation is deterministic, and stale trust cannot persist indefinitely.

---

## MC-28 — Conflict/precedence policy engine

**Priority:** P1 — policy correctness  
**Related INV-22 controls:** C019, C024, C041–C048, C055, C076–C077, C099, C100  

**Target state:** Resolve conflicts among compatibility, security, residency, SLO, cost, and operational constraints with deterministic fail-closed precedence and explainable decisions.

### Implementation checklist

- [ ] Define a typed policy input model containing workload certification, site branch/baseline, security requirements, residency constraints, resource/SLO constraints, exception/waiver state, and relevant topology facts.
- [ ] Codify precedence rules with security/isolation/residency constraints non-bypassable except through an explicit approved waiver mechanism; document all permitted overrides.
- [ ] Use deterministic policy evaluation with versioned policy bundles and a stable decision schema: allow/deny/defer plus reason codes and matched rule IDs.
- [ ] Reject ambiguous/conflicting rules at policy validation time or define an explicit priority/deny-overrides algorithm; never depend on file ordering accidentally.
- [ ] Record policy version/digest and relevant input fact revisions with every admission/certification decision.
- [ ] Support dry-run/evaluation mode for proposed policy changes against recorded fixture/workload sets before activation.
- [ ] Prevent policy from changing a semantic classification; policy may constrain use of a classified interface but cannot redefine divergent as shimmable.
- [ ] Integrate waiver/exception records with expiry so temporary bypasses automatically cease to apply.

### Verification and negative-test checklist

- [ ] Create table-driven tests for pairwise and multi-constraint conflicts including security vs cost, residency vs failover, SLO vs resource cap, and branch compatibility vs placement.
- [ ] Mutation-test rule priority/deny handling to ensure safety-critical precedence is covered by tests.
- [ ] Replay historical decisions against new policy in dry-run mode and report behavior changes before activation.

### Required evidence/artifacts

- [ ] Versioned policy schema/bundle and precedence specification.
- [ ] Conflict decision fixture corpus.
- [ ] Explain/replay report showing rule IDs and input revisions.

### Exit criterion

- [ ] **DONE only when:** Every conflicting constraint set produces a deterministic, explainable, version-bound decision, and policy cannot silently weaken semantic or security invariants.

---

## MC-29 — Requirements traceability artifact

**Priority:** P0 — certification evidence blocker  
**Related INV-22 controls:** C020, C029–C030, C081–C090, C100  

**Target state:** Create a generated requirements traceability matrix linking all 100 INV-22 controls to implementation, tests, runtime evidence, owner, status, and release gate.

### Implementation checklist

- [ ] Define a machine-readable RTM schema with `check_id`, requirement text hash/version, implementation references, test IDs, evidence artifact references/digests, status, owner, reviewer, waiver ID, and last-verified revision.
- [ ] Populate exactly one primary record for every `INV-22-C001` through `INV-22-C100`; fail generation on missing, duplicate, or unknown IDs.
- [ ] Resolve code/test references to repository paths plus symbols/line-independent anchors where practical and validate referenced files exist.
- [ ] Map each runtime/CI evidence reference to immutable artifact digests and release/build IDs rather than local filesystem names only.
- [ ] Distinguish `implemented`, `verified`, `blocked`, `not-applicable`, and `waived`; require reason/approver/expiry for N/A or waived states.
- [ ] Generate human-readable Markdown/HTML summary from the machine-readable source, not vice versa.
- [ ] Add stale-reference detection when code/tests are removed or a requirement text changes.
- [ ] Make the production exit gate require all mandatory controls verified or covered by valid approved exception policy.

### Verification and negative-test checklist

- [ ] Delete a test/code reference and verify RTM validation fails.
- [ ] Alter a requirement ID/text and ensure stale mappings are flagged for review.
- [ ] Run a completeness check asserting 100 unique control IDs and no dangling evidence references.

### Required evidence/artifacts

- [ ] Machine-readable 100-row RTM.
- [ ] Generated human-readable traceability report.
- [ ] RTM validation CI artifact tied to the release commit.

### Exit criterion

- [ ] **DONE only when:** All 100 checklist items have current, machine-verifiable implementation/test/evidence linkage and the release gate consumes this artifact directly.

---

## MC-30 — Integration test suite

**Priority:** P0 — release blocker  
**Related INV-22 controls:** C030, C051–C060, C083–C084, C089–C090, C100  

**Target state:** Exercise INV-22 with real or contract-faithful adjacent layers, durable state, selected WASI/WASIX runtimes, and control-plane/admission paths.

### Implementation checklist

- [ ] Define an integration topology covering INV-22, `pk_core`, INV-13, INV-11, INV-12, INV-10, GAP-14, matrix/cert stores, and at least one approved runtime per branch.
- [ ] Provide deterministic test environment provisioning using containers/VMs/local processes as appropriate, with all versions pinned.
- [ ] Cover end-to-end flows: interface discovery → matrix generation/approval → shim use/refusal → certification issuance → site branch selection → admission/run refusal/allow → audit/evidence emission.
- [ ] Include upgrade/downgrade scenarios across supported contract versions and matrix/certificate schema migrations.
- [ ] Include dependency timeout/unavailability, stale certification, revoked certificate, matrix drift, wrong branch, and translator failure scenarios.
- [ ] Assert persisted side effects and telemetry/audit outputs, not just return codes.
- [ ] Make tests hermetic with isolated state and deterministic cleanup; no dependency on developer-local services or paths.
- [ ] Split smoke vs full integration suites so pull requests get a fast safety signal while release/nightly jobs run complete scenarios.

### Verification and negative-test checklist

- [ ] Run all success and fail-closed scenarios from a clean provisioned environment.
- [ ] Repeat selected tests under network delay/loss and process restarts.
- [ ] Execute the suite against min/max supported adjacent/runtime versions.

### Required evidence/artifacts

- [ ] Pinned integration-environment manifest.
- [ ] CI integration logs plus preserved machine-readable results.
- [ ] End-to-end evidence chain and audit trace for representative allow/refuse flows.

### Exit criterion

- [ ] **DONE only when:** A release candidate passes repeatable end-to-end integration tests against all required adjacent boundaries and approved branch runtimes with both success and failure paths verified.

---

## MC-31 — Reference/conformance fixtures

**Priority:** P0 — contract verification foundation  
**Related INV-22 controls:** C022, C026, C029, C082–C085, C090, C100  

**Target state:** Publish stable golden and negative fixtures for matrix, shim, certification, policy, errors, and representative branch interface payloads.

### Implementation checklist

- [ ] Create a versioned `fixtures/` hierarchy by contract and schema version, separating `valid`, `invalid`, `edge`, `security`, and `forward_compat` cases.
- [ ] For each fixture, include expected parse/validation verdict and where applicable canonical output bytes/digest and expected error code.
- [ ] Include minimal and maximal valid objects, empty optional fields, boundary integers, Unicode/path data, all enum/variant alternatives, unknown optional fields, duplicate/ambiguous IDs, and malformed encodings.
- [ ] Add signed certification fixtures for valid/expired/revoked/wrong-issuer/tampered scenarios using test-only keys clearly separated from production trust.
- [ ] Add translator vectors for each shimmable interface/direction and refusal vectors for divergent/unclassified interfaces.
- [ ] Add cross-version fixtures demonstrating explicitly supported backward/forward compatibility and intentionally unsupported major-version cases.
- [ ] Store fixture provenance: schema/baseline digest and generator version; regenerate only through a reviewed deterministic tool.
- [ ] Expose fixture validation as a standalone command usable by adjacent component teams.

### Verification and negative-test checklist

- [ ] Run every fixture through parser/validator/translator/verifier and compare exact expected result/error code.
- [ ] Validate canonical fixtures with a second implementation/schema engine where practical.
- [ ] Ensure test-only signing keys cannot be accepted by production trust configuration.

### Required evidence/artifacts

- [ ] Versioned fixture corpus and manifest.
- [ ] Expected-result metadata/digests.
- [ ] Cross-implementation fixture conformance report.

### Exit criterion

- [ ] **DONE only when:** Every public contract and semantic classification has portable positive/negative fixtures that downstream teams can use to verify interoperable behavior.

---

## MC-32 — Differential runtime test harness

**Priority:** P0 — semantic proof blocker  
**Related INV-22 controls:** C011, C029–C031, C061–C070, C083–C088, C090, C100  

**Target state:** Run equivalent workloads against approved standards-WASI and WASIX runtimes and compare normalized observable behavior to detect semantic drift and translator defects.

### Implementation checklist

- [ ] Define a runtime adapter interface for instantiate/run/invoke, capability configuration, stdin/stdout/stderr capture, filesystem/network sandbox setup, exit/error capture, and resource measurements.
- [ ] Pin one or more approved runtime versions for each branch and record runtime-specific feature flags/configuration in the test manifest.
- [ ] Create small deterministic workload modules per interface that exercise normal, boundary, error, rights/capability, concurrency, and lifecycle behavior.
- [ ] Normalize known non-semantic differences (timestamps, runtime-specific diagnostics, nondeterministic identifiers) through explicit versioned comparators rather than broad text filtering.
- [ ] Compare return values, errors, side effects, filesystem/network state, resource ownership, ordering constraints, and security capability effects as applicable.
- [ ] Exercise direct native behavior plus behavior through the INV-22 translator to prove the shim closes only the intended representational gap.
- [ ] Capture complete per-run provenance: module digest, runtime/version/config, branch baseline, matrix/translator version, host architecture, and random seed.
- [ ] Turn newly observed unexplained differences into blocking counterexamples until classified and reviewed.

### Verification and negative-test checklist

- [ ] Run identical-interface workloads without shims and require equivalent normalized traces.
- [ ] Run shimmable-interface workloads through both translation directions and require invariant-preserving equivalence.
- [ ] Run divergent-interface workloads and prove the harness sees/refuses the known semantic difference rather than normalizing it away.
- [ ] Repeat across supported runtime versions/architectures to separate branch semantics from one-runtime bugs.

### Required evidence/artifacts

- [ ] Runtime adapter/harness implementation and pinned manifest.
- [ ] Normalized trace schema and counterexample corpus.
- [ ] Differential comparison report consumed by certification.

### Exit criterion

- [ ] **DONE only when:** Every `IDENTICAL`/`SHIMMABLE` claim used for production certification is backed by repeatable differential traces on approved runtimes; unexplained differences block release.

---

## MC-33 — Cross-platform/architecture testing

**Priority:** P1 — portability assurance  
**Related INV-22 controls:** C012–C013, C031, C061–C070, C084, C088, C093, C100  

**Target state:** Prove supported behavior across declared host operating systems, CPU architectures, runtime implementations, hypervisors/providers, and Python versions without assuming one developer machine represents production.

### Implementation checklist

- [ ] Publish a support matrix listing each supported host OS, CPU architecture, Python version, WASI runtime/version, WASIX runtime/version, and optional hypervisor/provider combination.
- [ ] Define which combinations are tier-1 release-gating, tier-2 regularly tested, and explicitly unsupported; avoid claiming support for untested cells.
- [ ] Configure CI/self-hosted runners to cover at least the declared tier-1 combinations and collect architecture/runtime identity into test evidence.
- [ ] Exercise schema parsing, matrix classification, translation, signing/verifying, durable storage, CLI/API behavior, and end-to-end differential tests on each tier-1 cell.
- [ ] Include filesystem/path/case-sensitivity, line-ending, locale/Unicode, clock/timezone, socket/network-stack, process model, and file-locking differences in platform-specific tests.
- [ ] Verify binary/tool dependencies exist for each architecture and are pinned by architecture-specific digest where applicable.
- [ ] Track platform-specific exceptions as explicit support limitations/waivers rather than conditional skips with no owner.
- [ ] Require support-matrix review whenever a runtime/toolchain drops an OS/architecture or adds materially different behavior.

### Verification and negative-test checklist

- [ ] Run the same conformance fixture corpus across all tier-1 cells and compare machine-readable verdicts.
- [ ] Exercise ARM64 and x86_64 integer/alignment/serialization boundary cases where applicable.
- [ ] Test Windows/Linux path and filesystem semantic differences against translator invariants.

### Required evidence/artifacts

- [ ] Machine-readable platform support matrix.
- [ ] Per-cell CI result artifacts with exact environment identity.
- [ ] Documented unsupported combinations and approved exceptions.

### Exit criterion

- [ ] **DONE only when:** Every advertised tier-1 platform/runtime combination passes the same release-gating contract and integration suites, and untested combinations are not presented as supported.

---

## MC-34 — Fuzzing/property-based testing

**Priority:** P1 — robustness/security  
**Related INV-22 controls:** C041, C050, C081–C087, C090, C100  

**Target state:** Continuously explore malformed, adversarial, and boundary inputs for schemas, interface identifiers, translators, certificates, policy, and storage codecs.

### Implementation checklist

- [ ] Add property-based generators for interface names/versions, matrix entries, shim payloads, certificate metadata, branch values, error details, configuration, and state transitions.
- [ ] Add coverage-guided fuzz targets for every untrusted parser/decoder and any binary/structured payload codec used by `PK_BRANCH_*` contracts.
- [ ] Seed fuzz corpora with valid fixtures, historical bugs, maximal nesting/lengths, Unicode/path edge cases, duplicate keys/IDs, integer boundaries, and malformed signatures.
- [ ] Define safety properties: no crash/hang, bounded memory/time, deterministic validation result, no acceptance of invalid signatures/classifications, and no capability widening.
- [ ] Add stateful/model-based fuzzing for certification lifecycle, config activation, branch transitions, and migration logic when those components exist.
- [ ] Persist minimized crashing/failing inputs as regression fixtures and record the code/schema version that fixed them.
- [ ] Run a bounded fuzz smoke job on pull requests and longer scheduled fuzz campaigns with timeout/resource budgets.
- [ ] Collect coverage and deduplicate findings by stack/property/error signature; treat security-relevant parser crashes as release blockers.

### Verification and negative-test checklist

- [ ] Demonstrate fuzzers can rediscover seeded intentional parser/validation faults in a mutation branch or test harness.
- [ ] Run long-duration campaigns without unbounded memory growth or unreproducible hangs.
- [ ] Replay the entire minimized corpus deterministically on every release candidate.

### Required evidence/artifacts

- [ ] Fuzz target inventory and corpus manifest.
- [ ] Coverage/crash summary from scheduled campaigns.
- [ ] Regression fixtures derived from all fixed fuzz findings.

### Exit criterion

- [ ] **DONE only when:** All untrusted parsing/translation/state-machine surfaces have automated property/fuzz coverage, and every discovered failure becomes a permanent regression case.

---

## MC-35 — Security test suite

**Priority:** P0 — production security blocker  
**Related INV-22 controls:** C041–C050, C081–C090, C100  

**Target state:** Translate the threat model into executable adversarial tests covering trust boundaries, privilege, tampering, replay, confused deputy, resource abuse, and supply-chain assumptions.

### Implementation checklist

- [ ] Create a threat-to-test matrix mapping each threat/abuse case to one or more automated tests and expected security invariant.
- [ ] Test authentication and authorization bypass, principal/resource substitution, stale/revoked credentials, issuer confusion, downgrade attempts, and cross-environment/site access.
- [ ] Test matrix/certificate/signature tampering, baseline digest substitution, malicious schema payloads, replayed certificates, and rollback to known-vulnerable revisions.
- [ ] Test confused-deputy scenarios in which an authorized translator/control plane is induced to perform an action on behalf of an unauthorized workload.
- [ ] Test capability/rights amplification across translations, especially filesystem/network/process rights and resource-handle ownership.
- [ ] Test resource-exhaustion attacks against payload size, nesting, decompression/serialization, queue/concurrency, audit/storage, and expensive semantic diff paths.
- [ ] Test tenant/workload data leakage through errors, logs, traces, caches, diagnostics, fixture exports, and high-cardinality labels.
- [ ] Test supply-chain failure modes: untrusted package source, altered dependency artifact, unsigned release, stale SBOM/vulnerability policy, and unapproved runtime baseline.
- [ ] Add security regression tests for every confirmed vulnerability and preserve exploit-shaped input in a safe test fixture.

### Verification and negative-test checklist

- [ ] Run the suite with least-privilege test identities and verify denials occur at the correct boundary.
- [ ] Perform periodic independent/manual penetration review focused on assumptions automation cannot fully cover.
- [ ] Verify security tests run in CI/release gates with no broad skip/xfail policy for production-critical controls.

### Required evidence/artifacts

- [ ] Threat-model-to-test traceability matrix.
- [ ] Automated security test report and failure artifacts.
- [ ] Independent review/penetration findings with remediation closure records.

### Exit criterion

- [ ] **DONE only when:** Every material threat has an executable test or documented manual verification, and production release is blocked by unresolved critical security-test failures.

---

## MC-36 — Performance/benchmark suite

**Priority:** P1 — performance gate foundation  
**Related INV-22 controls:** C013, C061–C070, C088, C090, C100  

**Target state:** Establish reproducible performance baselines for classification, matrix validation/load, translation, certification verification, persistence, startup, and end-to-end admission.

### Implementation checklist

- [ ] Define benchmark operations and dataset sizes: single/batch classify, small/large matrix load+validate, each translator, cert sign/verify/store lookup, policy decision, inventory/diff, and cold/warm startup.
- [ ] Measure latency distributions (at least p50/p95/p99), throughput, CPU time, allocations/RSS, I/O, and serialized bytes where relevant.
- [ ] Separate microbenchmarks from end-to-end benchmarks and record host CPU/architecture, OS, Python/runtime version, power mode, and background-load controls.
- [ ] Provide fixed benchmark fixtures representing typical, high-cardinality, and worst-supported-size inputs.
- [ ] Warm up runtimes/caches explicitly and label cold versus warm results; do not compare mixed conditions.
- [ ] Persist baseline results by release and calculate statistically meaningful regression deltas with noise tolerance.
- [ ] Set release thresholds only after measuring representative environments; encode thresholds in machine-readable policy.
- [ ] Profile regressions to attribute time/allocation to parsing, serialization, translator logic, crypto, storage, or dependency calls.

### Verification and negative-test checklist

- [ ] Repeat benchmark runs and report variance/confidence; flag unstable benchmarks before using them as gates.
- [ ] Inject a known slowdown/allocation increase and verify regression detection triggers.
- [ ] Benchmark both branch directions and representative identical/divergent refusal paths to ensure failures remain cheap.

### Required evidence/artifacts

- [ ] Benchmark harness and fixed input corpus.
- [ ] Versioned baseline results with environment metadata.
- [ ] Machine-readable performance gate thresholds and regression report.

### Exit criterion

- [ ] **DONE only when:** Release candidates are compared against reproducible performance baselines, and approved startup/throughput/tail-latency/resource regressions are automatically enforced.

---

## MC-37 — Capacity/load/stress tests

**Priority:** P1 — scalability/resilience  
**Related INV-22 controls:** C017, C028, C054, C061–C069, C088, C100  

**Target state:** Determine sustainable capacity, overload behavior, recovery characteristics, and fairness rather than relying on functional correctness under low load.

### Implementation checklist

- [ ] Define load models for read-heavy matrix/classify traffic, translator-heavy traffic, certification verify/store traffic, config/policy updates, and mixed production-like traffic.
- [ ] Exercise steady-state, burst, ramp-to-saturation, sustained overload, scale-out/scale-in, and post-overload recovery scenarios.
- [ ] Vary matrix size, payload size, concurrent clients/workloads, certificate-store size, audit rate, and dependency latency to find dominant capacity dimensions.
- [ ] Measure throughput, tail latency, queue depth, rejection rate, CPU, memory/RSS, allocation rate, storage IOPS/latency, and dependency pool utilization.
- [ ] Validate fairness so one workload/principal/interface cannot monopolize concurrency or queue capacity beyond configured policy.
- [ ] Establish maximum tested capacities and an operational safe operating envelope below hard saturation.
- [ ] Verify admission/load shedding activates before memory/latency collapse and that rejected work carries stable overload errors.
- [ ] Verify recovery to baseline latency/resource usage after overload stops and detect leaked tasks/handles/connections/caches.

### Verification and negative-test checklist

- [ ] Run load until each documented saturation signal trips and verify observed capacity matches model/tolerance.
- [ ] Hold sustained overload for a soak interval and confirm bounded memory/queue/storage growth.
- [ ] Remove load and verify recovery without restart unless restart is explicitly part of the design.

### Required evidence/artifacts

- [ ] Capacity model and safe operating envelope.
- [ ] Load/stress result artifacts and saturation graphs.
- [ ] Operational scaling/admission thresholds derived from tests.

### Exit criterion

- [ ] **DONE only when:** Saturation points, safe capacity, rejection behavior, fairness, and recovery are measured and encoded into operational thresholds rather than inferred.

---

## MC-38 — Failure-injection/chaos tests

**Priority:** P1 — resilience proof  
**Related INV-22 controls:** C048, C051–C060, C089, C092, C095, C100  

**Target state:** Prove documented recovery and fail-closed invariants under process, storage, dependency, network, corruption, stale-state, and partial-update failures.

### Implementation checklist

- [ ] Build injectable failure points around config activation, cert issuance/revocation, store transactions, trust/key lookup, baseline fetch, matrix publication, audit append, and site-branch transition.
- [ ] Inject process termination/restart at transactional boundaries and verify crash consistency.
- [ ] Inject dependency timeout, connection refusal, malformed response, stale version, and partial availability separately for every adjacent service.
- [ ] Inject disk-full/read-only/corruption/slow-storage conditions for durable state and audit persistence.
- [ ] Inject network partition and duplicate/stale controller behavior to validate fencing/split-brain protection.
- [ ] Inject expired/revoked certification and trust-store staleness while traffic is active and verify new unsafe admissions stop promptly.
- [ ] Inject failed rollback/migration steps and require deterministic quarantine/manual-recovery state rather than continuing ambiguously.
- [ ] Record recovery time, lost/duplicated operations, audit continuity, and invariant violations for each experiment.

### Verification and negative-test checklist

- [ ] Automate a fault matrix with expected state/return code/telemetry for each injection point.
- [ ] Repeat selected chaos scenarios under load to expose timing/race failures.
- [ ] Verify every experiment leaves the environment recoverable/reconstructable and audit evidence intact.

### Required evidence/artifacts

- [ ] Fault-injection matrix and automation.
- [ ] Recovery objective/result report per scenario.
- [ ] Captured audit/evidence proving fail-closed outcomes.

### Exit criterion

- [ ] **DONE only when:** Critical failure modes have repeatable injected tests that meet documented recovery objectives without silent branch/certification/policy invariant violation.

---

## MC-39 — Telemetry backend/exporter

**Priority:** P0 — production observability blocker  
**Related INV-22 controls:** C071–C080, C090–C091, C100  

**Target state:** Implement structured metrics, logs, and traces with stable semantics and a production exporter rather than descriptive signal names only.

### Implementation checklist

- [ ] Define a telemetry semantic-convention document for operation names, result/error codes, branch, interface, schema version, component ID, site/environment, and bounded workload identifiers.
- [ ] Implement metrics for matrix counts/completeness, shim calls/refusals/errors/latency, certification verify/issue/revoke outcomes, uncertified-run attempts, drift, queue/saturation, dependency health, and config/branch transitions.
- [ ] Implement structured logs with stable event IDs and fields; use bounded values and avoid serializing payloads, certificates, tokens, paths, or secrets by default.
- [ ] Implement trace spans across public operation → policy → translator/store/dependency boundaries and propagate trace context over supported RPC/HTTP transports.
- [ ] Integrate an exporter such as the project-approved OpenTelemetry path and define behavior when export is unavailable (bounded buffering/drop policy; never block security-critical logic indefinitely).
- [ ] Control metric/log cardinality: interface names may be bounded from the approved inventory, but arbitrary component/workload IDs require careful aggregation or log-only detail.
- [ ] Attach release/build/config/matrix revision to resource attributes so incidents can be correlated with changes.
- [ ] Add redaction/filtering hooks and privacy classification before export.

### Verification and negative-test checklist

- [ ] Golden-test metric/log/span schemas and required fields for allow/refuse/error flows.
- [ ] Disable the telemetry collector and verify bounded local behavior with no application deadlock or unbounded buffer growth.
- [ ] Scan exported telemetry for marker secrets/payload data and high-cardinality explosions.

### Required evidence/artifacts

- [ ] Telemetry schema/semantic-convention specification.
- [ ] Exporter configuration and sample metrics/logs/traces.
- [ ] Redaction/cardinality/outage test results.

### Exit criterion

- [ ] **DONE only when:** Operators can observe rate/errors/latency/saturation and branch/certification state through structured exportable telemetry without leaking secrets or destabilizing runtime behavior.

---

## MC-40 — Health/readiness endpoint

**Priority:** P0 — operability/admission blocker  
**Related INV-22 controls:** C052, C071, C077, C091–C092, C100  

**Target state:** Expose machine-readable liveness/readiness/version/configuration/dependency/capability state so orchestration and operators can distinguish alive from safe-to-serve.

### Implementation checklist

- [ ] Define separate liveness and readiness semantics; liveness must be cheap/local, while readiness may include required store/trust/matrix/dependency freshness checks.
- [ ] Report build/version, supported contract versions, active config revision, active matrix digest/revision, active site branch/baseline, trust-store revision, and capability set in a protected diagnostic endpoint/CLI.
- [ ] Represent dependency state individually with status, version, freshness/last-success time, and whether it is readiness-critical.
- [ ] Include certification/policy store health and audit sink health; define when each causes `not_ready`, `degraded`, or warning only.
- [ ] Protect detailed health information through authentication/authorization when it reveals topology/configuration, while allowing a minimal orchestration probe if required.
- [ ] Use stable reason codes and bounded timeouts so a health request cannot itself hang on a failed dependency.
- [ ] Expose state-transition timestamps and previous failure reason to help diagnose flapping without dumping sensitive internals.
- [ ] Document readiness behavior during startup, migration, offline mode, branch transition, degraded dependencies, and emergency freeze.

### Verification and negative-test checklist

- [ ] Test every readiness-critical dependency failure/staleness combination and expected status/reason code.
- [ ] Ensure liveness remains responsive during dependency outage/overload while readiness changes appropriately.
- [ ] Verify unauthorized callers receive only the intended minimal health surface.

### Required evidence/artifacts

- [ ] Health/readiness schema and state table.
- [ ] Probe integration tests for startup/degraded/failure/recovery.
- [ ] Sample sanitized operator diagnostics.

### Exit criterion

- [ ] **DONE only when:** Orchestrators and operators can deterministically tell whether INV-22 is alive, ready, degraded, stale, or frozen and why, using stable machine-readable state.

---

## MC-41 — Audit/event log

**Priority:** P0 — security/accountability blocker  
**Related INV-22 controls:** C036, C041, C044–C050, C073, C076, C078–C079, C090, C097–C100  

**Target state:** Create an append-only, integrity-protected security audit stream for every sensitive decision/change with actor, object, before/after revision, and reason.

### Implementation checklist

- [ ] Define audit event types for authentication/authorization denial, matrix publish/classification change, shim refusal/security failure, cert issuance/verification failure/revocation, trust/key change, config activation/rollback, branch transition, waiver use, and emergency controls.
- [ ] Define a versioned event schema with event ID, monotonic sequence, timestamp plus trusted-time quality, principal, action, resource IDs, environment/site, old/new digest/revision, result/reason code, trace/correlation ID, and policy version.
- [ ] Make events append-only and tamper-evident using a hash chain, signed checkpoints, WORM-capable sink, or equivalent project-approved design.
- [ ] Write security-critical audit events transactionally with state changes where feasible, or use an outbox pattern so committed state cannot silently lack its corresponding event.
- [ ] Define bounded redaction/minimization: never store raw secrets or unnecessary payload content; hash/pseudonymize identifiers where policy requires it.
- [ ] Implement local buffering and recovery behavior for temporary sink outage, including a hard limit and explicit safe behavior if the audit channel cannot accept critical events.
- [ ] Protect read/export access independently from write authority and detect sequence gaps/replay/duplicate event IDs.
- [ ] Provide verification tooling that validates chain/checkpoint integrity and reports the first broken/missing sequence.

### Verification and negative-test checklist

- [ ] Tamper/delete/reorder/duplicate audit records in a test copy and verify integrity tooling detects each condition.
- [ ] Inject audit sink outage during a state-changing operation and verify the documented transactional/outbox/fail-closed behavior.
- [ ] Confirm audit events for denied operations do not leak credential or payload secrets.

### Required evidence/artifacts

- [ ] Versioned audit event schema.
- [ ] Integrity/checkpoint design and verifier output.
- [ ] Audit outage/tamper test evidence.

### Exit criterion

- [ ] **DONE only when:** All security-sensitive operations are attributable and tamper-evident, committed state changes cannot silently bypass auditing, and event-chain integrity is independently verifiable.

---

## MC-42 — Alerting/SLO automation

**Priority:** P1 — operational readiness  
**Related INV-22 controls:** C052, C061–C070, C071–C080, C091, C097, C100  

**Target state:** Turn stated SLOs into executable service-level indicators, recording rules, burn-rate alerts, dashboards, and operator actions.

### Implementation checklist

- [ ] Define SLIs for `no silent divergence`, matrix completeness, drift reporting freshness, translation availability/latency, certification verification, dependency freshness, and security refusal rates.
- [ ] For “no budget” invariants, define immediate page/block conditions such as any admitted uncertified run or active unclassified interface rather than percentage-based tolerance.
- [ ] For availability/latency objectives, define request population, success criteria, excluded policy denials, windows, and target percentile/threshold.
- [ ] Create recording rules and multi-window burn-rate alerts where error budgets apply; create direct invariant alerts for zero-budget conditions.
- [ ] Create dashboards showing active branch/baseline/matrix revision, certification status, unclassified count, shim refusal/error trends, dependency health, saturation, and recent changes.
- [ ] Route alerts by severity/owner and attach runbook links and relevant explain/audit queries.
- [ ] Suppress/deduplicate expected rollout noise only through explicit maintenance/change context, never by disabling core security alerts globally.
- [ ] Test alert expressions against synthetic telemetry and historical incidents/fixtures before production use.

### Verification and negative-test checklist

- [ ] Inject an uncertified-run attempt, unclassified interface, stale drift report, dependency outage, and latency/queue saturation and verify intended alerts fire.
- [ ] Verify policy refusals do not incorrectly consume availability SLO unless defined to do so.
- [ ] Test alert recovery/clear behavior and ensure flapping does not hide persistent faults.

### Required evidence/artifacts

- [ ] SLO/SLI specification and machine-readable thresholds.
- [ ] Dashboard/recording/alert rule definitions.
- [ ] Synthetic alert test and runbook-link verification report.

### Exit criterion

- [ ] **DONE only when:** Production SLOs are computed automatically from defined signals, zero-budget invariant breaches page/block immediately, and every alert links to actionable operator guidance.

---

## MC-43 — Drift history persistence

**Priority:** P1 — governance/observability  
**Related INV-22 controls:** C004, C016, C036, C071–C080, C093, C098–C100  

**Target state:** Persist release-by-release divergence history with provenance so trend decisions are based on durable data rather than the in-memory `DriftReport.releases` dictionary.

### Implementation checklist

- [ ] Define a drift record schema containing release/build ID, standards/fork baseline digests, matrix digest, counts by classification, added/removed/reclassified interfaces, generator version, timestamp, and signer/producer.
- [ ] Persist records in append-only/revisioned durable storage and prevent modification of historical release data except through an auditable correction mechanism.
- [ ] Compute deltas versus previous release and optionally long-term baseline, including newly divergent and resolved divergence counts rather than only a scalar total.
- [ ] Link each changed interface to its semantic diff/proof/review record so operators can inspect why drift changed.
- [ ] Define retention that preserves enough history for supported-version and deprecation decisions; back up the history alongside other durable control state.
- [ ] Expose query/export by release, interface, classification, baseline pair, and time range.
- [ ] Record provenance from CI/release pipeline so a drift record cannot be mistaken for an ad-hoc local run.
- [ ] Detect missing release records and duplicate/conflicting release IDs.

### Verification and negative-test checklist

- [ ] Record multiple synthetic releases including growth, reduction, reclassification, and interface removal and verify computed deltas.
- [ ] Restart/restore storage and confirm complete ordered history.
- [ ] Attempt to overwrite a historical release and verify policy blocks or audits the correction path.

### Required evidence/artifacts

- [ ] Drift-history schema and durable records.
- [ ] Release trend report with per-interface deltas.
- [ ] History integrity/backup-restore test evidence.

### Exit criterion

- [ ] **DONE only when:** Every release produces one durable provenance-bound drift record with reproducible per-interface deltas and no silent history mutation.

---

## MC-44 — Drift threshold/policy action

**Priority:** P1 — release governance  
**Related INV-22 controls:** C013, C019, C070, C076–C077, C091–C093, C099–C100  

**Target state:** Define what divergence growth is acceptable, review-required, deprecation-triggering, or release-blocking and make the policy executable.

### Implementation checklist

- [ ] Define policy dimensions beyond raw count: critical-interface divergence, new divergence, unresolved age, unsupported translator loss, certification impact, and affected workload population.
- [ ] Classify interfaces by criticality/security sensitivity so one high-risk new divergence can block even when total divergence count is unchanged.
- [ ] Specify release thresholds and required actions such as automatic block, architecture/security review, deprecation plan, migration milestone, or approved time-bounded waiver.
- [ ] Evaluate policy against the durable drift record and matrix diff in CI before certification/release approval.
- [ ] Emit stable decision/reason codes and include policy version/digest, threshold values, and changed interfaces in the release evidence.
- [ ] Prevent a waiver from altering historical drift data; waivers may authorize release under a condition but must remain visible and expire.
- [ ] Define ownership and escalation for threshold breaches and overdue divergent interfaces.
- [ ] Review thresholds periodically against actual incident/maintenance cost rather than weakening them ad hoc during a release.

### Verification and negative-test checklist

- [ ] Create fixture histories just below/at/above every threshold and verify deterministic policy result.
- [ ] Test a critical-interface divergence blocks even when aggregate count is below a generic threshold if policy says so.
- [ ] Test waiver expiry automatically restores the blocking result.

### Required evidence/artifacts

- [ ] Versioned drift policy and criticality taxonomy.
- [ ] CI gate results tied to release drift record.
- [ ] Waiver/escalation evidence for any permitted exception.

### Exit criterion

- [ ] **DONE only when:** Divergence trend has explicit risk-based release consequences enforced automatically, with all exceptions time-bounded and auditable.

---

## MC-45 — Operator CLI/API

**Priority:** P1 — operations/control surface  
**Related INV-22 controls:** C021–C028, C036, C044, C049, C071, C076–C077, C092, C096–C100  

**Target state:** Provide supported authenticated operator interfaces for inspection and controlled mutation rather than requiring direct Python imports or datastore edits.

### Implementation checklist

- [ ] Define commands/endpoints for version/health, dependency status, matrix list/show/diff/validate, classify proposal/review status, translate fixture, cert issue/show/verify/revoke, drift report, config validate/show/activate/rollback, branch status/transition, and audit verification.
- [ ] Use the same typed domain/service layer as automation; CLI/API wrappers must not implement alternate policy/authz logic.
- [ ] Return stable exit codes and optional machine-readable JSON output in addition to concise human-readable output.
- [ ] Require authentication/authorization for mutation and sensitive reads; support explicit target environment/site and prevent accidental default-to-production behavior.
- [ ] Add `--dry-run`/plan mode for configuration, policy, matrix publication, certification issuance, and branch transition where useful.
- [ ] Require confirmation or non-interactive explicit flags for destructive/high-impact operations while preserving automation usability.
- [ ] Include request/correlation ID and audit event reference in mutation responses.
- [ ] Document API compatibility/versioning and rate/size limits; generate command/API reference from the canonical schema where feasible.

### Verification and negative-test checklist

- [ ] Contract-test JSON output/exit codes/error codes for every command/endpoint.
- [ ] Test unauthorized and wrong-environment/site mutations are rejected.
- [ ] Test dry-run output matches the eventual applied diff/revision for unchanged state.

### Required evidence/artifacts

- [ ] CLI/API specification and generated help/reference.
- [ ] Contract fixture suite for success/error cases.
- [ ] Audit records proving privileged operator actions are attributable.

### Exit criterion

- [ ] **DONE only when:** Operators can perform all supported inspection and lifecycle actions through a versioned, authenticated, auditable interface without editing internal state directly.

---

## MC-46 — Deployment artifacts

**Priority:** P1 — deployment readiness  
**Related INV-22 controls:** C005–C006, C031–C040, C047, C061–C080, C092–C096, C100  

**Target state:** Package INV-22 for the intended execution environment with immutable artifacts, least-privilege runtime identity, resource limits, health probes, and reproducible configuration wiring.

### Implementation checklist

- [ ] Choose and document supported deployment forms (library-only, standalone service, container, system service, Kubernetes workload, etc.); provide artifacts only for declared forms.
- [ ] For containers, use a minimal pinned base by digest, non-root user, read-only root filesystem where possible, explicit writable state mounts, dropped capabilities, and no shell/tooling not required at runtime.
- [ ] For orchestrated deployments, define resource requests/limits, liveness/readiness probes, disruption/rollout strategy, service account/identity, network policy, and persistent-volume semantics as applicable.
- [ ] Mount immutable schema/baseline artifacts read-only and mutable config/state separately; inject secrets by provider reference rather than baking them into images/manifests.
- [ ] Pin all image/package dependencies and publish platform architectures supported by each artifact.
- [ ] Add security context and filesystem/network permissions consistent with the least-privilege threat model.
- [ ] Emit version/build/SBOM/provenance labels and make runtime health report the same build identity.
- [ ] Provide deployment validation/linting and a smoke test that starts from the packaged artifact, not the source checkout.

### Verification and negative-test checklist

- [ ] Deploy each supported artifact into a clean representative environment and run readiness plus end-to-end smoke tests.
- [ ] Verify non-root/readonly/capability/network constraints do not require hidden privileged fallbacks.
- [ ] Scan the final artifact for vulnerabilities, secrets, unexpected files, and architecture mismatch.

### Required evidence/artifacts

- [ ] Versioned deployment manifests/image definition/service files.
- [ ] Artifact scan and deployment smoke-test report.
- [ ] Runtime build-identity output matched to release metadata.

### Exit criterion

- [ ] **DONE only when:** Supported deployment artifacts start reproducibly with least privilege and validated configuration, pass health/integration smoke tests, and expose verifiable release identity.

---

## MC-47 — Bootstrap automation

**Priority:** P0 — reproducibility/Day-0 blocker  
**Related INV-22 controls:** C031–C040, C046, C071, C096, C100  

**Target state:** Provide a deterministic Day-0 path from a clean supported host/environment to a healthy verified INV-22 installation without undocumented manual steps.

### Implementation checklist

- [ ] Create a bootstrap entry point that checks OS/architecture/Python/runtime prerequisites, available disk/memory, required trust roots, and access to approved package/artifact sources.
- [ ] Install strictly from locked/pinned dependencies and verify hashes/signatures before activation.
- [ ] Create required state/config directories with least-privilege ownership/permissions and never write outside documented locations.
- [ ] Generate or validate an initial configuration from a checked-in secure template; require explicit environment/site identity and branch baseline rather than guessing.
- [ ] Initialize/migrate stores transactionally and seed only public schemas/baselines/trust material appropriate to the target environment.
- [ ] Run post-install self-checks: import/version, schema validation, store write/read, trust verification, matrix load, health/readiness, and a safe fixture translation/cert verification.
- [ ] Make bootstrap idempotent: rerunning on an already initialized compatible install should validate/repair permitted drift without duplicating state or overwriting operator changes.
- [ ] Produce a machine-readable bootstrap report including versions/digests, actions, validation results, and any manual follow-up; redact secrets.

### Verification and negative-test checklist

- [ ] Run from a pristine supported host/container/VM and assert no preexisting developer tools/paths are required beyond documented prerequisites.
- [ ] Interrupt bootstrap at each stateful phase, rerun, and verify consistent recovery/idempotency.
- [ ] Test unsupported host/toolchain and signature/hash failure paths fail before partial activation.

### Required evidence/artifacts

- [ ] Bootstrap script/tool and prerequisite manifest.
- [ ] Clean-environment bootstrap CI log and machine-readable report.
- [ ] Idempotency/interruption recovery test results.

### Exit criterion

- [ ] **DONE only when:** A clean supported environment can reach healthy readiness through one documented deterministic bootstrap path whose inputs are pinned and whose result is self-verified.

---

## MC-48 — Rollback implementation

**Priority:** P0 — safe-release blocker  
**Related INV-22 controls:** C037–C038, C057–C059, C092, C095–C097, C100  

**Target state:** Turn conceptual rollback into executable, transactional recovery for code/config/matrix/policy/cert-store schema changes without violating trust or branch invariants.

### Implementation checklist

- [ ] Define rollback units separately: application artifact, config revision, matrix/policy revision, site branch transition, translator version, and data/schema migration.
- [ ] Retain the previous known-good immutable artifact and signed configuration/matrix/policy revisions needed to return safely.
- [ ] Before rollback, evaluate backward data/schema compatibility and explicitly block rollback when new durable state cannot be safely read by the older version without a reverse migration.
- [ ] Implement authorized rollback commands/API with expected-current-revision protection and dry-run impact analysis.
- [ ] Quiesce or fence writes when required, apply rollback atomically, re-run validation/readiness, and automatically re-enable traffic only after health gates pass.
- [ ] Never “rollback” by resurrecting revoked certifications, retired keys, known-vulnerable dependency pins, or policy explicitly barred by security controls.
- [ ] Persist rollback reason, actor, from/to versions/digests, affected workloads, and verification result in the audit stream.
- [ ] Define automatic rollback triggers for staged rollout only when they are unambiguous and cannot amplify a security incident; otherwise freeze and require operator action.

### Verification and negative-test checklist

- [ ] Perform release N→N+1→N rollback drills with representative durable state and verify data/audit/cert integrity.
- [ ] Test rollback refusal after an intentionally irreversible migration and verify safe quarantine guidance.
- [ ] Inject failure during rollback and verify recovery reaches a defined safe state rather than mixed revisions.

### Required evidence/artifacts

- [ ] Rollback compatibility matrix and executable procedure.
- [ ] Rollback drill/fault-injection evidence.
- [ ] Audit record demonstrating attributable before/after revisions and health verification.

### Exit criterion

- [ ] **DONE only when:** Supported changes have tested executable rollback or an explicitly documented non-rollback migration strategy; rollback cannot revive unsafe trust/security state.

---

## MC-49 — Migration tooling

**Priority:** P1 — data/schema lifecycle  
**Related INV-22 controls:** C015–C016, C027, C032–C038, C057, C093, C095, C100  

**Target state:** Provide version-aware, resumable migration for matrix schemas, certification records/stores, policy/config, and shim payload formats as contracts evolve.

### Implementation checklist

- [ ] Inventory every versioned durable/external format and assign independent schema versions with explicit upgrade/downgrade compatibility.
- [ ] Implement ordered migration steps with source version, destination version, preconditions, transformation, postconditions, and reversibility metadata.
- [ ] Use copy-on-write or transactional migrations for security-critical state; never overwrite the only known-good copy before post-migration verification passes.
- [ ] Validate cryptographic bindings carefully: signed certificates should normally remain immutable; migrations should preserve original signed bytes and build indexes/wrappers rather than rewriting signed content.
- [ ] Provide dry-run planning that reports item counts, unsupported records, expected storage/time, required downtime/quiescence, and rollback feasibility.
- [ ] Make migrations resumable/idempotent with durable checkpoints and explicit handling of partially processed records.
- [ ] Block service activation on an unsupported on-disk/config schema rather than silently best-effort parsing it.
- [ ] Record migration tool version, source/destination schema versions, actor/build, input/output digests/checksums, and verification result.

### Verification and negative-test checklist

- [ ] Test every supported N→N+1 path and supported multi-hop upgrade from the oldest maintained version.
- [ ] Interrupt migrations at multiple checkpoints and verify resume without duplicate/lost records.
- [ ] Test malformed/unknown/future records and verify deterministic quarantine/refusal.
- [ ] Compare pre/post semantic state and audit/certificate verification after migration.

### Required evidence/artifacts

- [ ] Migration registry/scripts and compatibility table.
- [ ] Golden pre/post datasets with semantic-equivalence checks.
- [ ] Migration interruption/rollback verification report.

### Exit criterion

- [ ] **DONE only when:** All supported version transitions are executable, validated, resumable, and provenance-recorded; unsupported state versions prevent unsafe startup.

---

## MC-50 — Release automation/CI

**Priority:** P0 — release blocker  
**Related INV-22 controls:** C020, C031, C040, C045, C050, C061–C070, C081–C090, C092–C100  

**Target state:** Create a deterministic CI/release pipeline that builds, tests, scans, signs, and emits complete acceptance evidence before any production release.

### Implementation checklist

- [ ] Define required CI stages: format/lint, type analysis, compile/import, unit/property tests, contract/fixture tests, full `pk_core` conformance, integration/differential tests, security tests, coverage, package build, SBOM/vulnerability scan, artifact verification/signing, and release gate.
- [ ] Pin CI actions/images/toolchains by immutable versions/digests where supported and minimize token/secret permissions per job.
- [ ] Run supported Python/OS/architecture/runtime matrix jobs and separate fast pull-request jobs from full scheduled/release qualification without weakening release requirements.
- [ ] Build release artifacts once in a controlled build stage; downstream tests/signing/publishing must consume the exact built artifact rather than rebuilding from source independently.
- [ ] Attach source commit, dirty-tree status, dependency lock digest, schema/baseline/matrix digests, toolchain versions, and build environment identity to release metadata.
- [ ] Require branch protection/review and successful mandatory gates before release/tag publication; do not permit manual “green override” outside the formal waiver process.
- [ ] Publish machine-readable test/gate/coverage/SBOM/vulnerability/provenance/signature artifacts with deterministic naming and retention.
- [ ] Add release rollback/emergency-disable metadata and supported-version update as part of the release transaction/checklist.

### Verification and negative-test checklist

- [ ] Run the pipeline from a clean tag/commit and verify all artifacts reference exactly that source revision.
- [ ] Intentionally fail each critical gate and confirm release publication is blocked.
- [ ] Verify CI jobs have only required secrets/permissions and fork/untrusted contributions cannot access signing/publishing credentials.

### Required evidence/artifacts

- [ ] Version-controlled CI/release workflow definitions.
- [ ] Complete release evidence bundle for a candidate build.
- [ ] Permission/threat review of the CI signing/publish path.

### Exit criterion

- [ ] **DONE only when:** No production artifact can be published without passing the full mandatory gate set, and every release is traceable to one immutable source/build/evidence set.

---

## MC-51 — Static analysis/type checking configuration

**Priority:** P1 — code-quality/security gate  
**Related INV-22 controls:** C050, C081, C087, C090, C094, C100  

**Target state:** Enforce consistent linting, type safety, security analysis, and dead-code/import hygiene as automated gates.

### Implementation checklist

- [ ] Select and configure a formatter/linter (for example Ruff or project equivalent) with rules covering correctness, unsafe exception handling, unused code/imports, complexity hotspots, and modern Python practices.
- [ ] Configure strict-enough static typing (mypy/pyright or equivalent) for domain contracts, schemas, translators, stores, and public APIs; explicitly track any untyped third-party boundary.
- [ ] Add security-oriented static analysis (Bandit or equivalent) and targeted checks for subprocess/shell use, unsafe deserialization, temp files, path traversal, TLS verification, and cryptographic misuse.
- [ ] Define import/package layering rules so domain logic does not accidentally depend on deployment/UI internals or bypass authorization/storage abstractions.
- [ ] Treat new warnings/errors as CI failures; grandfathered debt must be listed explicitly with owner/reason/expiry rather than suppressed globally.
- [ ] Enable unreachable-code and exhaustive-enum/union checks where tooling supports them, especially around classifications, lifecycle states, and error codes.
- [ ] Run analysis against test code as appropriate to catch bad fixtures/security assumptions, while allowing narrowly documented test-specific exceptions.
- [ ] Pin analyzer versions/configuration and record them in release evidence to prevent silent rule drift.

### Verification and negative-test checklist

- [ ] Seed representative violations in a test branch and verify each configured analyzer blocks CI.
- [ ] Ensure type checking catches an omitted classification/error/state variant after enum expansion.
- [ ] Review suppression counts automatically and fail on unapproved blanket ignores.

### Required evidence/artifacts

- [ ] Committed lint/type/security-analysis configuration.
- [ ] CI analysis reports and suppression/debt inventory.
- [ ] Analyzer version manifest.

### Exit criterion

- [ ] **DONE only when:** Static analysis runs on every change with pinned rules, no unowned blanket suppressions, and errors in security/correctness-critical code block merge/release.

---

## MC-52 — Coverage measurement/gate

**Priority:** P1 — test adequacy control  
**Related INV-22 controls:** C020, C081–C090, C100  

**Target state:** Measure test coverage by line/branch and critical semantic path, then enforce thresholds that prevent untested compatibility/security logic from entering release.

### Implementation checklist

- [ ] Configure coverage collection with branch coverage enabled and source scoping that excludes generated/vendor code but includes all INV-22 domain/service/security logic.
- [ ] Set an overall minimum only after baseline measurement, plus higher/explicit requirements for critical files/functions such as classification, translators, certification verification, authorization, lifecycle transitions, and migration.
- [ ] Track changed-line coverage so new code cannot hide behind historical high coverage.
- [ ] Require tests for every classification enum arm, structured error family, lifecycle state transition, authorization decision family, and translator direction.
- [ ] Combine unit/property/contract/integration coverage where technically feasible and clearly label what execution tiers contribute to the metric.
- [ ] Generate human-readable and machine-readable reports and preserve them with release evidence.
- [ ] Prevent exclusion pragmas from being added without review/reason; audit existing exclusions.
- [ ] Use mutation testing selectively on critical semantic/security modules to measure whether covered code is actually asserted meaningfully.

### Verification and negative-test checklist

- [ ] Add an uncovered critical branch and verify the appropriate gate fails.
- [ ] Run mutation testing against classification/shim/cert enforcement and confirm representative semantic changes are killed.
- [ ] Validate report paths/source mapping for packaged and CI environments.

### Required evidence/artifacts

- [ ] Coverage configuration and threshold policy.
- [ ] Line/branch/changed-line coverage reports.
- [ ] Mutation-test summary for critical modules.

### Exit criterion

- [ ] **DONE only when:** Release coverage meets documented thresholds, all critical state/error/classification paths are exercised, and new code cannot reduce coverage below policy without an explicit waiver.

---

## MC-53 — Software bill of materials (SBOM)

**Priority:** P1 — supply-chain evidence  
**Related INV-22 controls:** C031, C045, C050, C090, C094, C100  

**Target state:** Generate a machine-readable inventory of release contents and dependencies that can be tied cryptographically to the exact artifact.

### Implementation checklist

- [ ] Choose a standard SBOM format/profile (SPDX or CycloneDX as approved by the project) and generate it from the final built artifact/environment, not only source dependency declarations.
- [ ] Include package/component name/version, supplier/origin where known, hashes, licenses, dependency relationships, and relevant runtime/base-image components.
- [ ] Include `pk_core`, runtime adapters/tools shipped with the artifact, and vendored/generated schema assets where they materially affect the released component.
- [ ] Record the release artifact digest and source commit/provenance reference in SBOM metadata so consumers can bind inventory to bytes.
- [ ] Validate SBOM schema and fail generation on malformed or missing required identity/hash fields.
- [ ] Diff SBOMs across releases and flag unexpected dependency additions/removals or version changes for review.
- [ ] Publish/store the SBOM alongside the signed artifact and release attestations with the same retention policy.
- [ ] Ensure SBOM generation cannot leak private registry credentials, local paths, tokens, or environment secrets.

### Verification and negative-test checklist

- [ ] Compare SBOM dependency inventory with the lock/build environment and investigate unexplained discrepancies.
- [ ] Verify the SBOM references the exact final artifact digest and survives independent schema validation.
- [ ] Build a release with an intentionally added dependency and ensure the SBOM diff surfaces it.

### Required evidence/artifacts

- [ ] Signed/attested SBOM per release.
- [ ] SBOM schema-validation and lock reconciliation report.
- [ ] Release-to-release dependency diff.

### Exit criterion

- [ ] **DONE only when:** Every released artifact has a validated, non-secret-bearing SBOM bound to its digest and reconciled against the locked dependency/build contents.

---

## MC-54 — Vulnerability scanning

**Priority:** P0 — security/release blocker  
**Related INV-22 controls:** C041, C045, C050, C090, C094, C100  

**Target state:** Continuously scan source/dependencies/artifacts for known vulnerabilities and insecure patterns with severity, exploitability, support, and waiver policy.

### Implementation checklist

- [ ] Run dependency vulnerability scanning against the locked environment/SBOM and include transitive packages.
- [ ] Run static code/security scanning and, for container/deployment artifacts, scan the final image/base OS packages as applicable.
- [ ] Define severity/exploitability thresholds that block release and a time-bound remediation SLA by severity.
- [ ] Pin/record vulnerability database timestamp/version so a release report is reproducible and can be distinguished from later intelligence.
- [ ] Deduplicate findings across scanners and record package/path, advisory ID, fixed version if available, reachability/exploitability assessment, owner, and disposition.
- [ ] Treat “no fixed version” separately from “not vulnerable”; require mitigation or documented risk acceptance rather than silently ignoring it.
- [ ] Integrate scan results with the waiver mechanism including approver, rationale, compensating controls, and expiration.
- [ ] Schedule rescans of supported released versions so newly disclosed vulnerabilities can trigger patching even when source has not changed.

### Verification and negative-test checklist

- [ ] Seed/use a known-vulnerable test dependency in an isolated test and verify policy blocks at the configured threshold.
- [ ] Verify an expired vulnerability waiver re-blocks the release/support status.
- [ ] Confirm supported-release rescan workflow can identify a newly published advisory and route ownership.

### Required evidence/artifacts

- [ ] Machine-readable vulnerability reports tied to artifact/SBOM digest.
- [ ] Severity/remediation/waiver policy.
- [ ] Supported-release rescan and response evidence.

### Exit criterion

- [ ] **DONE only when:** Release artifacts have current vulnerability evidence, blocking thresholds are automated, and supported versions are continuously re-evaluated as advisory data changes.

---

## MC-55 — Artifact signing/attestation

**Priority:** P0 — supply-chain trust blocker  
**Related INV-22 controls:** C045, C049–C050, C090, C094, C100  

**Target state:** Provide verifiable signatures and build provenance for release artifacts, SBOMs, and critical policy/schema bundles so consumers can detect substitution and trace build origin.

### Implementation checklist

- [ ] Select the project-approved signing/attestation mechanism and define trust roots, signer identity requirements, verification policy, and keyless/keyed lifecycle as applicable.
- [ ] Sign or attest the final wheel/sdist/container/deployment bundle digests after all release-gating tests complete; never sign mutable staging artifacts that are later modified.
- [ ] Generate build provenance recording source repository/commit, builder identity, build workflow, dependency/lock digest, build parameters, and resulting artifact digest.
- [ ] Bind SBOM and conformance/evidence bundle digests into the release attestation or publish independently verifiable signed attestations for each.
- [ ] Protect signing permissions so pull-request/untrusted jobs cannot invoke release signing; use short-lived isolated credentials or managed signing service where possible.
- [ ] Publish verification instructions/tooling that checks artifact signature, provenance, source identity, and required attestations before install/deploy.
- [ ] Define signer/key compromise response, revocation, rotation, and re-verification of still-supported releases.
- [ ] Record signing/verification events in audit/release metadata without exposing private material.

### Verification and negative-test checklist

- [ ] Modify a signed artifact/SBOM/provenance file and prove verification fails.
- [ ] Attempt signing from an unauthorized CI context and verify denial.
- [ ] Exercise key/signer rotation and revocation against old/new release artifacts.

### Required evidence/artifacts

- [ ] Release signatures and provenance attestations.
- [ ] Verifier output included in deployment/bootstrap tests.
- [ ] Signer permission/rotation test evidence.

### Exit criterion

- [ ] **DONE only when:** Every production artifact and critical release metadata is cryptographically bound to an authorized build/source identity and independently verifiable before deployment.

---

## MC-56 — License/NOTICE files

**Priority:** P1 — distribution/legal readiness  
**Related INV-22 controls:** C002, C008–C010, C031, C053, C100  

**Target state:** Make redistribution and third-party attribution terms explicit for the repository and packaged artifacts.

### Implementation checklist

- [ ] Select/confirm the project-approved repository license with the authorized owner; do not infer terms from neighboring repositories.
- [ ] Add the exact canonical license text as `LICENSE` and add `NOTICE` when required by the chosen license/project policy.
- [ ] Declare the license in package metadata using the current packaging-standard mechanism and ensure wheel/sdist include the license files.
- [ ] Inventory third-party dependencies/assets whose licenses require attribution, notice propagation, source offer, or other obligations.
- [ ] Generate or maintain a third-party notice report and ensure it corresponds to the locked/SBOM dependency set.
- [ ] Detect incompatible or policy-disallowed dependency licenses during dependency review/CI.
- [ ] Document ownership for legal/license review when adding vendored code, generated definitions, or runtime binaries.
- [ ] Add a release check confirming `LICENSE`/`NOTICE` and required attributions are present in distributable artifacts.

### Verification and negative-test checklist

- [ ] Inspect built wheel/sdist/container/package to confirm required license/notice files are present.
- [ ] Compare third-party notice inventory to the SBOM/lock and flag missing/new licenses.
- [ ] Fail CI on a deliberately disallowed/unknown-license test package according to project policy.

### Required evidence/artifacts

- [ ] `LICENSE`, `NOTICE`/third-party notice artifacts as required.
- [ ] Package metadata showing declared license.
- [ ] License policy/check report tied to the release SBOM.

### Exit criterion

- [ ] **DONE only when:** Repository and release artifacts carry explicit approved license terms and all required third-party notices/obligations are reconciled against the release contents.

---

## MC-57 — Security policy

**Priority:** P0 — vulnerability-response readiness  
**Related INV-22 controls:** C041–C050, C091, C094, C097–C100  

**Target state:** Document supported versions, vulnerability reporting, response expectations, disclosure handling, and security ownership.

### Implementation checklist

- [ ] Add `SECURITY.md` stating which release lines are supported for security fixes and how support status is determined.
- [ ] Provide an approved private vulnerability reporting channel and expected acknowledgement/triage cadence; avoid directing sensitive reports to public issue trackers.
- [ ] Define severity/priority framework, remediation targets, embargo/disclosure coordination, and criteria for emergency release or disablement.
- [ ] Define roles for security triage, technical owner, release authority, communications, and adjacent-component coordination.
- [ ] Document how dependency/runtime/WASI/WASIX upstream vulnerabilities are assessed for reachability and impact to INV-22.
- [ ] Define handling of compromised signing keys/certification issuers, including trust-root revocation and affected certification/release identification.
- [ ] Define security advisory content requirements: affected/fixed versions, mitigations, CVE/advisory IDs when applicable, artifact/signature references, and upgrade/rollback guidance.
- [ ] Connect `SECURITY.md` to incident runbooks and vulnerability-scanning/waiver processes.

### Verification and negative-test checklist

- [ ] Run a tabletop vulnerability report from intake through triage, fix, release, advisory, and verification.
- [ ] Run a signing/certification key compromise tabletop and verify affected artifacts can be enumerated from provenance/audit data.
- [ ] Verify public documentation reveals no sensitive internal escalation details/secrets while still giving reporters a usable path.

### Required evidence/artifacts

- [ ] `SECURITY.md` and supported-version policy.
- [ ] Tabletop exercise record with corrective actions.
- [ ] Security ownership/escalation roster in the project-approved location.

### Exit criterion

- [ ] **DONE only when:** Reporters have a clear secure intake path, supported versions and response expectations are explicit, and the team has tested vulnerability/key-compromise response procedures.

---

## MC-58 — Contribution/ownership metadata

**Priority:** P1 — governance/maintainability  
**Related INV-22 controls:** C009–C010, C020, C041, C098–C100  

**Target state:** Make code ownership, review responsibilities, change requirements, and contributor workflow explicit so critical compatibility/security decisions cannot drift without accountable review.

### Implementation checklist

- [ ] Add `CONTRIBUTING.md` covering environment/bootstrap, tests/gates, coding/style/type rules, commit/PR expectations, fixture/schema update procedures, and how to propose matrix classifications.
- [ ] Add `CODEOWNERS` or equivalent for contract/schema, matrix/proofs/translators, certification/crypto, security/authz, storage/migrations, deployment/CI, and documentation/runbooks.
- [ ] Require specialist review for security-sensitive or semantic-classification changes and define minimum reviewer count/approval type.
- [ ] Document maintainers and escalation roles in a durable project-controlled location rather than only personal knowledge.
- [ ] Define how breaking public-contract changes are proposed (ADR/RFC), reviewed with adjacent component owners, and versioned.
- [ ] Require tests/evidence/RTM updates in the contribution checklist when implementation affects a control.
- [ ] Define contribution rules for generated artifacts and prohibit hand-editing generated matrix/schema outputs without the source/generator change.
- [ ] Document security-sensitive local setup so contributors do not need production secrets/keys to run tests.

### Verification and negative-test checklist

- [ ] Validate CODEOWNERS patterns actually cover the intended critical files.
- [ ] Use PR-template/check automation to detect missing tests/RTM/schema regeneration for representative changes.
- [ ] Verify a new contributor can bootstrap and run the documented local validation path without undocumented access.

### Required evidence/artifacts

- [ ] `CONTRIBUTING.md`, ownership metadata, PR/change templates.
- [ ] Critical-path ownership coverage report.
- [ ] Contributor bootstrap/test verification log.

### Exit criterion

- [ ] **DONE only when:** Every critical artifact has accountable ownership/review rules, contribution requirements are executable/documented, and semantic/security changes cannot merge without the designated review path.

---

## MC-59 — Operational runbooks

**Priority:** P0 — Day-2 readiness blocker  
**Related INV-22 controls:** C052, C059–C060, C071–C080, C091–C097, C100  

**Target state:** Provide executable operator procedures for normal operation and high-risk failure scenarios with commands, decision points, validation, escalation, and recovery criteria.

### Implementation checklist

- [ ] Create runbooks for startup/readiness failure, matrix incompleteness/divergence spike, shim refusal spike, uncertified-run attempt, certificate verification/revocation issue, trust/key compromise, dependency outage, storage/audit failure, configuration rollback, and site branch mismatch/split-brain.
- [ ] For each runbook, state trigger signals/alerts, impact/risk, prerequisites/permissions, immediate containment, diagnostic queries/commands, decision tree, remediation, validation, rollback/fallback, escalation, and post-incident evidence to preserve.
- [ ] Use only supported CLI/API operations; do not instruct operators to edit databases/files directly unless an explicit last-resort recovery procedure with safeguards exists.
- [ ] Include exact invariant checks before returning service to ready, such as matrix completeness zero gaps, cert/trust freshness, single active branch revision, and audit-chain continuity.
- [ ] Link runbooks from alerts/health reason codes and keep command output examples sanitized.
- [ ] Version runbooks with supported release lines and update them whenever CLI/API/architecture changes.
- [ ] Define emergency freeze/disable actions that prioritize stopping unsafe admissions while preserving evidence.
- [ ] Add post-incident steps for RTM/test regression updates when an incident exposed a missing control.

### Verification and negative-test checklist

- [ ] Execute tabletop and hands-on drills for at least the highest-severity scenarios using a staging environment.
- [ ] Verify runbook commands/options remain valid through automated doc/runbook smoke tests where practical.
- [ ] Measure time to containment/recovery and capture unclear/missing steps as tracked corrective actions.

### Required evidence/artifacts

- [ ] Versioned runbook set indexed by alert/failure mode.
- [ ] Drill records with timing and corrective actions.
- [ ] Runbook link validation from alerting/health documentation.

### Exit criterion

- [ ] **DONE only when:** Operators can contain, diagnose, recover, and verify every critical documented failure using tested supported procedures without improvising unsafe state changes.

---

## MC-60 — Disaster-recovery/backup plan

**Priority:** P0 — durable-state recovery blocker  
**Related INV-22 controls:** C047, C051, C055–C058, C089, C095–C097, C100  

**Target state:** Define and test backup, restore, reconstruction, recovery-point, and recovery-time behavior for certification, configuration/policy, drift, audit, and other durable control state.

### Implementation checklist

- [ ] Classify durable datasets by authority and reconstructability: signed certificates, revocation/supersession state, active config/policy revisions, site branch state, trust metadata, drift history, audit log/checkpoints, and derived caches/indexes.
- [ ] Define RPO/RTO targets per dataset and identify any state requiring synchronous replication or zero-loss treatment due to security semantics.
- [ ] Implement encrypted backups/snapshots with integrity hashes/signatures, retention schedule, geographic/residency constraints, and access separation from production writers.
- [ ] Ensure backups include schema/migration version and the immutable artifact/config references required to restore a compatible service.
- [ ] Define reconstruction procedures for derived indexes/caches from signed/source-of-truth records and validate reconstruction output.
- [ ] Design restore to a quarantined environment first; verify audit/cert/trust integrity and freshness before allowing restored state to serve admissions.
- [ ] Handle revocation freshness during restore so an old backup cannot resurrect credentials/certificates revoked after the snapshot; reconcile authoritative revocation state before readiness.
- [ ] Protect backup deletion/retention operations with separate privilege and audit them.

### Verification and negative-test checklist

- [ ] Perform full restore drills from recent and older supported backups and measure RPO/RTO against objectives.
- [ ] Corrupt/truncate a backup and verify integrity checks prevent restore/activation.
- [ ] Restore a snapshot predating a revocation and verify reconciliation prevents the revoked certificate from becoming valid.

### Required evidence/artifacts

- [ ] Backup/restore architecture and RPO/RTO table.
- [ ] Restore drill reports and integrity verification logs.
- [ ] Dataset reconstruction/revocation-reconciliation evidence.

### Exit criterion

- [ ] **DONE only when:** Critical state can be restored or reconstructed within approved objectives without reviving stale/revoked trust, and backup integrity/access is independently controlled.

---

## MC-61 — Data retention/privacy/residency controls

**Priority:** P1 — data governance  
**Related INV-22 controls:** C006, C019, C039, C046–C047, C073, C075, C079, C095, C098–C100  

**Target state:** Define what data INV-22 stores/emits, why it is needed, where it may reside, how long it is retained, and how identifiers/secrets are minimized and deleted.

### Implementation checklist

- [ ] Create a data inventory for certificates, component/workload/site identifiers, audit events, telemetry, configuration provenance, drift history, fixtures, support bundles, and backups.
- [ ] Classify each field/data set by sensitivity and determine whether it may contain customer/tenant/user-identifying information or secrets; redesign to avoid such data where not required.
- [ ] Define retention windows and legal/operational justification for live stores, audit, telemetry, backups, and test artifacts; distinguish immutable security evidence from disposable diagnostics.
- [ ] Implement deletion/expiration jobs for data with finite retention and test they cover primary, index, cache, and backup lifecycle according to policy.
- [ ] Define residency/location constraints for durable state and telemetry exporters and prevent failover/export to disallowed regions/sites.
- [ ] Apply encryption in transit/at rest to sensitive data with documented key ownership/rotation.
- [ ] Use pseudonymous/bounded identifiers in metrics/logs and prohibit raw payload/certificate secret material in telemetry.
- [ ] Document privacy-safe support bundle generation with explicit allowlist and operator review.

### Verification and negative-test checklist

- [ ] Insert marker sensitive values and verify they do not appear in disallowed telemetry/support outputs.
- [ ] Exercise retention expiry/deletion and confirm indexes/backups follow documented lifecycle.
- [ ] Simulate failover/export to a disallowed residency target and verify policy blocks it.

### Required evidence/artifacts

- [ ] Data inventory/classification/retention table.
- [ ] Residency/export policy and enforcement tests.
- [ ] Deletion/redaction/encryption verification evidence.

### Exit criterion

- [ ] **DONE only when:** Stored/exported data is minimized, classified, retention-bound, residency-aware, encrypted as required, and deletion/redaction controls are tested.

---

## MC-62 — Deprecation lifecycle

**Priority:** P1 — compatibility lifecycle  
**Related INV-22 controls:** C007–C008, C015–C016, C027, C044, C093–C094, C099–C100  

**Target state:** Provide a controlled path to deprecate/remove divergent interfaces, old schema/contract versions, translators, baselines, and obsolete certifications without surprise breakage or indefinite support.

### Implementation checklist

- [ ] Define lifecycle states such as supported → deprecated → blocked-for-new-certification → end-of-support → removed and the minimum notice/review period for each artifact type.
- [ ] Attach deprecation metadata to matrix entries/schemas/translators/baselines: announcement date, target removal release/date, replacement/migration path, owner, affected workload inventory, and rationale.
- [ ] Prevent new certifications from depending on artifacts that have entered a blocked-for-new-use state unless an explicit waiver exists.
- [ ] Emit warnings/telemetry when deprecated contracts/translators are used and provide an operator query listing impacted workloads/components.
- [ ] Define how existing certifications behave across deprecation and removal; do not silently reinterpret previously signed certification scope.
- [ ] Provide migration/conformance guidance and fixtures for replacements and verify affected workloads before final removal.
- [ ] Update supported-version matrices, documentation, runbooks, SBOM/dependencies, and RTM when deprecations advance state.
- [ ] Require final removal approval demonstrating zero supported workload dependency or approved exception handling.

### Verification and negative-test checklist

- [ ] Run a synthetic artifact through the full deprecation lifecycle and verify new issuance/use becomes blocked at the configured stage.
- [ ] Test telemetry/operator impact inventory includes all known dependent workloads.
- [ ] Attempt to use a removed schema/translator/baseline and verify stable unsupported-version/error behavior.

### Required evidence/artifacts

- [ ] Deprecation policy and machine-readable metadata schema.
- [ ] Affected-workload/dependency reports.
- [ ] Removal approval/migration evidence.

### Exit criterion

- [ ] **DONE only when:** Every obsolete interface/version/translator/baseline has a visible time-bound lifecycle, impact inventory, migration path, and deterministic enforcement at end of support.

---

## MC-63 — Formal governance/waiver mechanism

**Priority:** P0 — governance gate  
**Related INV-22 controls:** C009–C010, C019–C020, C041, C070, C090–C100  

**Target state:** Make all exceptions machine-readable, attributable, time-bounded, scoped, risk-assessed, and enforceable so release pressure cannot create invisible permanent bypasses.

### Implementation checklist

- [ ] Define a waiver schema with unique ID, control/policy finding, exact scope (release/environment/site/component/interface), rationale, risk statement, compensating controls, owner, approver(s), issue/expiry dates, and review cadence.
- [ ] Separate waiver requestor from approver for high-risk/security/semantic exceptions and require designated security/architecture approval where applicable.
- [ ] Cryptographically sign or otherwise integrity-protect approved waiver records and include their digest/IDs in the release/certification evidence they affect.
- [ ] Enforce scope and expiry automatically in the gate/policy engine; expired/out-of-scope waivers must have no effect.
- [ ] Prohibit waiver classes for non-waivable invariants explicitly designated by policy (for example accepting an unclassified interface as compatible without classification evidence).
- [ ] Require measurable compensating-control evidence and track remediation/technical-debt work to remove the waiver.
- [ ] Expose active waivers in health/explain/release reports and alert before expiry/overdue remediation.
- [ ] Retain expired/revoked waiver history in audit/governance records; never delete them to make historical release evidence look cleaner.

### Verification and negative-test checklist

- [ ] Test valid/in-scope, expired, revoked, wrong-release, wrong-environment, and tampered waiver behavior.
- [ ] Attempt to waive a designated non-waivable invariant and verify hard rejection.
- [ ] Verify release evidence enumerates every waiver that influenced the verdict and its compensating controls.

### Required evidence/artifacts

- [ ] Versioned waiver schema/policy.
- [ ] Signed/integrity-protected example waiver records and enforcement tests.
- [ ] Release report section listing active exceptions and expiry/remediation status.

### Exit criterion

- [ ] **DONE only when:** No exception can alter a gate invisibly or indefinitely: every waiver is scoped, approved, integrity-protected, automatically expires, and remains visible in historical evidence.

---

## MC-64 — Full local conformance evidence

**Priority:** P0 — final production-exit blocker  
**Related INV-22 controls:** C020, C029–C031, C040, C045, C081–C090, C100  

**Target state:** Produce a complete reproducible local evidence bundle proving all 100 INV-22 requirements against the actual packaged release, not just the standalone six-test core.

### Implementation checklist

- [ ] Resolve the `pk_core` dependency and all adjacent test dependencies so the repository can run the full conformance path from a clean checkout/artifact without skipped critical tests.
- [ ] Execute all 100 checklist assessments and emit one machine-readable result per `INV-22-C001…C100` with status, evidence references/digests, implementation version, and reviewer/gate metadata.
- [ ] Require zero unaccounted `SKIP`, `XFAIL`, `UNKNOWN`, `BLOCKED`, or missing controls in production evidence; approved N/A/waiver states must carry valid governance records.
- [ ] Run compile/import, unit/property, contract/fixture, integration/differential, security/fuzz, performance/capacity, failure-injection, platform compatibility, packaging/install, SBOM/vulnerability, and signature/provenance verification as required by the RTM.
- [ ] Run the `pk_core` evidence ledger generation and verify chain continuity/integrity from the prior approved evidence head if that framework requires chained release evidence.
- [ ] Generate the production gate result from the exact release artifact digest, matrix/config/policy/baseline digests, dependency lock, and CI build identity.
- [ ] Bundle all evidence with a manifest of SHA-256 or project-approved digests and sign/attest the evidence manifest alongside the release artifact.
- [ ] Provide a local verification command that checks artifact signature/provenance, evidence manifest integrity, RTM completeness, gate verdict, and all referenced required files without relying on developer memory.
- [ ] Archive the evidence bundle according to release/audit retention and link it to the supported-version record and rollback target.

### Verification and negative-test checklist

- [ ] Re-run verification in a separate clean environment using only the release artifact/evidence bundle/trust roots and confirm the same verdict.
- [ ] Delete or alter one evidence file and verify manifest/gate verification fails.
- [ ] Force one checklist item to blocked/failed and confirm the final production exit gate cannot report success.
- [ ] Verify all tests that were previously skipped solely for missing `pk_core` now execute and produce traceable results.

### Required evidence/artifacts

- [ ] 100-control machine-readable conformance result and RTM.
- [ ] Signed evidence manifest containing test, security, performance, SBOM/vulnerability, provenance/signature, drift, and gate artifacts.
- [ ] Independent clean-environment verification log.

### Exit criterion

- [ ] **DONE only when:** The exact release artifact can be independently verified from a clean environment to have complete, integrity-protected, non-skipped evidence for all mandatory INV-22 controls and a passing formal production exit gate.

---

## Final production-exit checklist

The 64 work packages above should converge into a single release decision. Before declaring INV-22 production-ready:

- [ ] All P0 work packages are complete; no P0 item remains merely documented as future work.
- [ ] All P1 items required by the selected production deployment profile are complete and linked to evidence.
- [ ] The requirements traceability matrix contains exactly 100 unique `INV-22-C001…C100` records with no dangling code/test/evidence references.
- [ ] `pk_core` full conformance executes without dependency-driven skips and the formal evidence chain verifies.
- [ ] The interface inventory is complete for every supported workload; unclassified interface count is zero.
- [ ] Every `SHIMMABLE` entry has a semantic proof, real bidirectional translator, round-trip/property evidence, and differential runtime evidence.
- [ ] Every `DIVERGENT` or unsupported interface fails closed with a stable structured reason and cannot be bypassed through policy/configuration.
- [ ] Certifications are durable, signed, artifact-bound, revocable, and enforced against the authoritative site branch/baseline.
- [ ] Authentication, authorization, secret handling, audit integrity, vulnerability scanning, artifact signing, and waiver governance pass security review and adversarial tests.
- [ ] Config/policy/matrix activation, migration, rollback, backup/restore, offline/reconnect, and branch-transition failure modes have been fault-injection tested.
- [ ] Performance/capacity thresholds are measured, machine-readable, and release-gated; overload remains bounded.
- [ ] Health/readiness, telemetry, SLOs/alerts, explain output, and runbooks are deployed and drill-tested.
- [ ] Package/deployment artifacts are reproducible from locked dependencies, include license/notice requirements, SBOM, vulnerability results, and signed provenance.
- [ ] The final evidence bundle is integrity-protected and independently re-verified against the exact production artifact digest in a clean environment.

**Completion standard:** INV-22 should not be considered a production implementation merely because its local core primitives pass. Production completion means the branch semantics, translators, certification trust chain, operational state, integrations, and release evidence are all independently reproducible and fail closed under unsupported or uncertain conditions.
