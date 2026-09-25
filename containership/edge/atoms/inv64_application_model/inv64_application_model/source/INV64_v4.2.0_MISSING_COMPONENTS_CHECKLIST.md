# INV-64 Application Model v4.2.0 — Comprehensive Missing-Component Remediation Checklist

**Source baseline:** post-hardening audit of `inv64_application_model` v4.2.0
**Scope:** all 40 missing-component groups MC-01 through MC-40 identified after the 4.2.0 hardening pass
**Purpose:** convert every residual gap into implementation-grade engineering work with explicit verification and release evidence.

## Checklist execution rules

- [ ] Treat a checkbox as complete only when the referenced artifact exists in the repository or release bundle and can be independently reproduced.
- [ ] For controls that affect runtime behavior, documentation alone is insufficient; require executable enforcement plus positive and negative tests.
- [ ] Every new public contract must be versioned, machine-readable, backwards-compatibility classified, and linked from `REQUIREMENTS_TRACEABILITY.md`.
- [ ] Every security-sensitive control must include an abuse/negative test proving fail-closed behavior.
- [ ] Every operational control must define ownership, alert/escalation destination, rollback behavior, and evidence retention.
- [ ] Every release-gating control must emit machine-readable evidence with tool version, source revision, input digest, timestamp, result, and failure details.
- [ ] Do not mark an item complete on the basis of an external system that cannot be reproduced from the repository's documented bootstrap path.
- [ ] Update `CHECKLIST.json`, `REQUIREMENTS_TRACEABILITY.md`, `AUDIT_REPORT.md`, and the release changelog whenever a missing component is closed.

## Severity handling

- **Critical:** blocks production certification; no waiver without explicit security/architecture approval, expiry date, and compensating controls.
- **High:** blocks general-availability release unless a time-bounded exception is formally accepted.
- **Medium:** may be deferred only when operational impact is understood, ownership is assigned, and the debt is tracked with an expiry date.

## MC-01 — Restore and govern the original `MASTER.md` master-prompt/workflow source corpus

**Severity:** High
**Traceability:** source provenance / claimed source set
**Objective:** Re-establish the authoritative source corpus that the repository claims to derive from, with immutable provenance and deterministic linkage to generated checklist/contract artifacts.

### Required deliverables
- [ ] Add the authoritative `MASTER.md` (or an explicitly versioned replacement source corpus) to the repository under a stable path.
- [ ] Add a provenance manifest such as `provenance/master-source.json` recording source name, source revision, SHA-256 digest, acquisition date, license/status, and custodian.
- [ ] Add a generated-source mapping that links source sections to `CHECKLIST.json`, `contract.py`, schemas, and workflow/gate artifacts.
- [ ] Add an integrity check that fails CI when the recorded source digest does not match the checked-in source corpus.

### Engineering / implementation checklist
- [ ] Identify the canonical source owner and repository/location; prohibit ambiguous copies with the same logical name but different contents.
- [ ] Normalize the source file encoding and line endings before hashing; document the normalization algorithm.
- [ ] Record whether `MASTER.md` is normative, informative, generated, or imported; define precedence if it conflicts with `CHECKLIST.json` or `contract.py`.
- [ ] Create a deterministic extractor/generator if checklist requirements are derived from the source; generated outputs must contain source section IDs.
- [ ] Add a CI job that regenerates derived artifacts and fails on uncommitted drift.
- [ ] Add a change-control rule requiring architecture/reviewer approval for normative source changes.
- [ ] Record historical source revisions used by previous releases so an auditor can reconstruct why a requirement existed at a given version.
- [ ] Add tests for missing source, wrong digest, duplicate source IDs, unmapped normative clauses, and generated-output drift.
- [ ] Update README language so it never claims a bundled source unless the exact artifact is present.
- [ ] Link source provenance into release evidence and SBOM/provenance metadata where applicable.

### Acceptance / closure criteria
- [ ] A clean checkout contains the authoritative source corpus and its provenance record.
- [ ] A deterministic verification command returns success for the committed source and fails after any unrecorded source mutation.
- [ ] Every normative source clause is either mapped to an implementation/checklist control or explicitly marked non-applicable with rationale.
- [ ] Release evidence contains the source digest used to certify the release.

## MC-02 — Provide a resolvable/bundled `pk_core` dependency and runnable full conformance environment

**Severity:** Critical
**Traceability:** C030, C040, C082, C090, C100
**Objective:** Make the integration dependency reproducible so the complete component contract and production gate can run from a clean environment without hidden local prerequisites.

### Required deliverables
- [ ] Choose and document the supported `pk_core` distribution model: pinned package dependency, workspace sibling, vendored subtree/submodule, or release artifact.
- [ ] Pin an exact `pk_core` version/revision and integrity digest; prohibit floating branch dependencies in certification paths.
- [ ] Add bootstrap automation for Windows and POSIX environments that creates an isolated runtime and installs/verifies the exact dependency set.
- [ ] Add a full conformance command that produces machine-readable pass/fail evidence rather than skip-only results.
- [ ] Add an offline/reproducible dependency path or clearly define the approved artifact mirror and cache policy.

### Engineering / implementation checklist
- [ ] Define the minimum and maximum supported Python versions and verify them against the selected `pk_core` revision.
- [ ] Declare `pk_core` through packaging metadata and fail installation with a clear diagnostic if version constraints cannot be satisfied.
- [ ] Verify `PK_CORE_PATH` fallback behavior, path normalization, symlink/junction handling, and rejection of untrusted/writable dependency locations for production certification.
- [ ] Add preflight diagnostics that report Python path, package version, source revision, dependency digest, and import origin.
- [ ] Run `tests/test_component.py` with zero unexpected skips in the certification environment.
- [ ] Run `python -m pk_core list`, `run INV-64`, `gate INV-64`, and evidence verification as part of CI/release gates.
- [ ] Capture stdout/stderr, exit status, environment metadata, and evidence artifacts for every conformance run.
- [ ] Add negative tests for missing dependency, wrong version, tampered package, incompatible Python, malformed evidence output, and gate tool failure.
- [ ] Ensure integration tests cannot convert dependency failures into success/green status.
- [ ] Document dependency upgrade procedure, rollback procedure, and compatibility validation requirements.

### Acceptance / closure criteria
- [ ] A clean supported host can bootstrap and run all integration tests from documented commands.
- [ ] No integration test is skipped because `pk_core` is absent in the production-certification job.
- [ ] The selected `pk_core` version and digest are visible in machine-readable release evidence.
- [ ] Tampering or version drift causes a hard gate failure before INV-64 is certified.

## MC-03 — Add installable package and dependency metadata

**Severity:** High
**Traceability:** C031, C040, C093
**Objective:** Make the repository an explicit, reproducible Python distribution with declared runtime, dependency, entry-point, version, and compatibility metadata.

### Required deliverables
- [ ] Add `pyproject.toml` using a modern PEP 517/518 build backend.
- [ ] Declare package name, dynamic/static version source, Python version range, runtime dependencies, optional test/dev dependencies, license, authors/maintainers, and project URLs.
- [ ] Define package discovery so schemas, examples, and required metadata are included in wheels/sdists.
- [ ] Add reproducible wheel/sdist build commands and package-install smoke tests.
- [ ] Add lock/constraints strategy for certification environments without over-constraining library consumers.

### Engineering / implementation checklist
- [ ] Make `VERSION` and Python package `__version__` derive from one authoritative source or verify equality in CI.
- [ ] Declare `pk_core` in the correct dependency group and pin/constraint policy according to MC-02/MC-30.
- [ ] Set `Requires-Python` and classifier metadata to the versions actually tested in CI.
- [ ] Add build-system isolation and verify no undeclared build dependency is imported from the developer machine.
- [ ] Include JSON schema and documentation assets in built artifacts; test access after wheel installation into an empty virtual environment.
- [ ] Run `pip check` or equivalent dependency-consistency validation after installation.
- [ ] Build both wheel and sdist; install each independently and run smoke/conformance subsets.
- [ ] Add package metadata linting and reject malformed metadata, missing license data, or unsupported Python versions.
- [ ] Record artifact digests and build backend versions in release evidence.
- [ ] Document editable-development install separately from production/certification installation.

### Acceptance / closure criteria
- [ ] `python -m build` succeeds from a clean checkout using only declared build dependencies.
- [ ] Fresh wheel and sdist installs expose the same public API, schema data, and version.
- [ ] Unsupported Python/dependency combinations fail with deterministic diagnostics.
- [ ] Release artifacts include package metadata sufficient for dependency, license, and provenance analysis.

## MC-04 — Assign accountable ownership, escalation path, and approved ADR

**Severity:** High
**Traceability:** C009-C010
**Objective:** Establish governance for architectural decisions, operational ownership, security escalation, and technology selection for INV-64.

### Required deliverables
- [ ] Add `OWNERS.md` or `CODEOWNERS`-equivalent metadata naming the accountable component owner role and backup role.
- [ ] Add an escalation matrix covering engineering, security, operations/SRE, and architecture review.
- [ ] Add an approved ADR for the application-model architecture and the decision to use/align with OAM concepts.
- [ ] Record decision status, date, approvers, context, alternatives, consequences, and supersession policy.

### Engineering / implementation checklist
- [ ] Use role/team identifiers instead of only personal names where continuity matters; define how current assignees are resolved.
- [ ] Define severity-based escalation timing and after-hours/on-call handling for production incidents.
- [ ] Document which decisions require owner approval versus security, architecture, or release-management approval.
- [ ] In the ADR, document the exact problem boundary, why declarative topology is chosen, interoperability expectations, and rejected alternatives.
- [ ] Record how the ADR relates to pinned OAM version/specification from MC-11.
- [ ] Add ADR IDs to relevant code/docs and traceability entries.
- [ ] Require review of ownership metadata on organizational changes and at a defined recurring cadence.
- [ ] Add a pull-request/release check that rejects production certification when accountable ownership is unresolved.
- [ ] Define emergency delegation and temporary ownership procedures with expiry.
- [ ] Archive superseded ADRs rather than deleting decision history.

### Acceptance / closure criteria
- [ ] An auditor can identify who is accountable for INV-64, how to escalate, and which architecture decision authorizes the design.
- [ ] The ADR is explicitly approved and not left in proposed/draft state for production.
- [ ] Ownership and ADR references are linked from `REQUIREMENTS_TRACEABILITY.md` and release-gate evidence.

## MC-05 — Complete SHALL-level semantic specification

**Severity:** High
**Traceability:** C011-C019
**Objective:** Define testable normative semantics for function, deployment tiers, outcomes, lifecycle, compatibility, capacity/fairness, disconnected operation, and constraint precedence.

### Required deliverables
- [ ] Create `SPECIFICATION.md` (or versioned specification directory) with normative RFC-2119/8174-style SHALL/SHOULD/MAY language.
- [ ] Define environment profiles for cloud, datacenter, near-edge, and far-edge where applicable.
- [ ] Define formal outcome classes: success, partial success, degraded, retryable failure, terminal failure, and rejected-before-activation.
- [ ] Define a lifecycle/state machine with legal transitions, transition guards, terminal states, and recovery paths.
- [ ] Define versioning/backward-compatibility rules, quota/fairness rules, disconnected behavior, and precedence hierarchy among security/residency/SLO/cost constraints.

### Engineering / implementation checklist
- [ ] Assign stable requirement IDs to every normative clause and map them to tests and implementation evidence.
- [ ] For each platform tier, specify supported features, required dependencies, resource ceilings, offline assumptions, and unsupported behaviors.
- [ ] Specify deterministic validation/canonicalization semantics for unknown extension fields, ordering, numeric types, Unicode normalization expectations, and schema evolution.
- [ ] Define capacity dimensions: payload bytes, components, providers, links, traits, concurrent submissions, per-tenant rate, queue depth, and memory/CPU budget.
- [ ] Define fairness policy under contention, including starvation prevention and admission/rejection semantics.
- [ ] Define intermittent-network behavior: local validation availability, cached dependencies, retry windows, stale configuration treatment, and reconciliation responsibility boundary.
- [ ] Define precedence when a valid manifest conflicts with security policy, residency rules, resource limits, cost policy, or SLO constraints; security should fail closed where specified.
- [ ] Specify compatibility promises for minor/patch releases and conditions requiring a major schema/API version.
- [ ] Create state-transition tables and corresponding test vectors for legal and illegal transitions.
- [ ] Review the normative specification for contradictions against `contract.py`, schema, README, and integration behavior.

### Acceptance / closure criteria
- [ ] Every C011-C019 requirement has an explicit normative clause and at least one verification method.
- [ ] No outcome, lifecycle state, quota decision, disconnected mode, or precedence conflict is left implementation-defined.
- [ ] Tests fail when behavior deviates from the normative state/compatibility/outcome rules.
- [ ] The specification version is included in release evidence.

## MC-06 — Formalize typed contracts for validation/canonical responses and WIT/RPC/control-plane bindings

**Severity:** High
**Traceability:** C021-C022, C026-C028
**Objective:** Eliminate untyped or prose-only integration boundaries by defining versioned schemas/IDLs for every externally visible request, response, error, and metadata envelope.

### Required deliverables
- [ ] Create an exhaustive interface inventory with boundary ID, direction, transport, caller/callee, auth context, schema/IDL, limits, and version.
- [ ] Define machine-readable request/response schemas for manifest validation, canonicalization, and error results.
- [ ] Where WIT/RPC/control-plane bindings exist, add the exact WIT/Proto/OpenAPI/JSON-Schema or equivalent IDL files.
- [ ] Define a versioned error envelope with stable code, path, message, retryability, correlation ID, and optional details.
- [ ] Add generated or hand-written conformance fixtures for every public operation.

### Engineering / implementation checklist
- [ ] Enumerate API, event, file, IPC, RPC, WIT, and control-plane boundaries; explicitly state when a boundary category is not applicable.
- [ ] Assign semantic versions to contract families independently where necessary; define compatibility rules for additive/removal/type changes.
- [ ] Represent validation issues as typed arrays with bounded size and deterministic ordering.
- [ ] Specify canonicalization response fields including digest algorithm, canonical-form version, digest value, and validation precondition status.
- [ ] Define payload size, concurrency, queue, connection, and response-size limits at each boundary.
- [ ] Define unknown-field and unknown-enum behavior to prevent parser/protocol differentials.
- [ ] Generate schema validation tests and cross-language fixtures where more than one implementation language is supported.
- [ ] Add backward/forward compatibility tests between supported contract versions.
- [ ] Prohibit undocumented fields or transport-specific semantics from becoming de facto API commitments.
- [ ] Link every interface schema to authentication/authorization policies from MC-07/MC-08.

### Acceptance / closure criteria
- [ ] Every external boundary in the inventory references an exact versioned machine-readable contract.
- [ ] Contract tests cover valid, invalid, boundary-limit, and version-mismatch cases.
- [ ] No public error path returns only free-form text without stable machine-readable classification.
- [ ] Generated contract documentation and fixtures are reproducible in CI.

## MC-07 — Define and enforce authentication at every submit/control-plane/provider boundary

**Severity:** Critical
**Traceability:** C023, C044
**Objective:** Ensure every actor that can submit, mutate, query, or influence application-model state is strongly authenticated before trust is granted.

### Required deliverables
- [ ] Create an authentication architecture document mapping each boundary to identity type, credential mechanism, trust root, and verification point.
- [ ] Implement authentication hooks/integration contracts for submitters, control-plane actors, nodes/peers, and providers.
- [ ] Define certificate/token/attestation validation policy including issuer, audience, subject, expiry, clock skew, revocation, and algorithm constraints.
- [ ] Add negative-path tests for unauthenticated, expired, revoked, wrong-audience, forged, and replayed credentials.
- [ ] Emit authentication success/failure audit events without leaking secret material.

### Engineering / implementation checklist
- [ ] Inventory human, workload, node, service, provider, artifact signer, and automation identities that interact with INV-64.
- [ ] Prefer workload identity or mutually authenticated transport for service-to-service boundaries; prohibit anonymous privileged operations.
- [ ] Define bootstrap trust establishment and rotation without relying on static shared secrets in manifests.
- [ ] Define behavior when identity services are unavailable, distinguishing cached-verifiable identity from unverifiable new trust.
- [ ] Bind authenticated identity to authorization context; prevent identity substitution across tenant boundaries.
- [ ] Protect authentication metadata against replay and downgrade; require nonce/channel binding where the selected protocol supports it.
- [ ] Set maximum credential/token lifetime and rotation expectations.
- [ ] Document break-glass identities, controls, audit requirements, and automatic expiry.
- [ ] Rate-limit repeated authentication failures at the calling boundary without creating a trivial tenant-to-tenant denial of service.
- [ ] Verify that diagnostics/logging redact tokens, certificates/private keys, and sensitive identity claims.

### Acceptance / closure criteria
- [ ] Every privileged boundary rejects unauthenticated actors before semantic processing or activation.
- [ ] Identity mechanism and trust roots are versioned/configurable without embedding credentials in the manifest.
- [ ] Security tests demonstrate failure on forged/replayed/expired/revoked credentials.
- [ ] Authentication evidence and audit events are correlated to the release/configuration operation they protect.

## MC-08 — Implement authorization and explicit least-privilege capability model

**Severity:** Critical
**Traceability:** C024, C042-C043
**Objective:** Constrain authenticated actors to explicit tenant-scoped operations and resources; eliminate ambient authority at integration boundaries.

### Required deliverables
- [ ] Define a capability/permission vocabulary for submit, validate, canonicalize, activate, rollback, inspect, administer, and provider-binding operations.
- [ ] Create a policy model mapping identities/roles to capabilities, tenant/environment scope, resource selectors, and conditions.
- [ ] Implement deny-by-default authorization checks at every state-changing and sensitive read boundary.
- [ ] Add policy-decision audit records including actor, action, resource, decision, policy version, and reason.
- [ ] Add authorization conformance and privilege-escalation tests.

### Engineering / implementation checklist
- [ ] Separate authentication from authorization and ensure no authenticated identity receives implicit administrator rights.
- [ ] Enforce tenant/environment/site scoping on every resource lookup and mutation.
- [ ] Define provider capability grants explicitly; never infer host filesystem/network/device authority from provider presence alone.
- [ ] Review `pk_core` integration authority and document every filesystem/network/process/device/secret capability actually required.
- [ ] Drop or sandbox unused ambient authority at process/container/WASM boundaries where available.
- [ ] Prevent confused-deputy paths in which one tenant can cause privileged actions on another tenant's resources.
- [ ] Define policy versioning, atomic policy activation, rollback, and fail-closed behavior for policy parse/verification errors.
- [ ] Add separation-of-duties controls for release approval, policy administration, and break-glass access where production context requires it.
- [ ] Create tests for horizontal/vertical privilege escalation, wildcard resource selectors, stale policy caches, and policy-service outage.
- [ ] Document least-privilege review cadence and evidence.

### Acceptance / closure criteria
- [ ] All privileged operations require an explicit capability decision with tenant/resource scope.
- [ ] Default/unknown capabilities are denied and cannot be enabled by manifest extension fields.
- [ ] Security tests demonstrate that cross-tenant and over-privileged actions are rejected.
- [ ] Authorization policy version is included in activation and audit evidence.

## MC-09 — Specify timeout, cancellation, retry, idempotency, backpressure, and peer-version negotiation semantics

**Severity:** High
**Traceability:** C025, C027, C053
**Objective:** Make distributed interactions bounded, retry-safe, cancellation-aware, overload-safe, and deterministic across supported peer versions.

### Required deliverables
- [ ] Create a transport/operation semantics matrix for each public/integration operation.
- [ ] Assign default and maximum deadlines/timeouts with caller-versus-server ownership rules.
- [ ] Define cancellation propagation and cleanup semantics.
- [ ] Define retryable error codes, retry budgets, jitter/backoff policy, and maximum attempt/elapsed-time limits.
- [ ] Define idempotency-key format/scope/retention and duplicate-request behavior for state-changing operations.
- [ ] Define bounded queues/backpressure/admission behavior and peer-version negotiation/downgrade policy.

### Engineering / implementation checklist
- [ ] Distinguish safe automatic retries from operations requiring caller-provided idempotency keys.
- [ ] Specify deadline propagation across adjacent layers and forbid resetting an exhausted end-to-end deadline at each hop.
- [ ] Define cancellation race semantics: canceled-before-start, canceled-in-flight, completed-concurrently, and irreversible-side-effect cases.
- [ ] Define overload responses and retry hints; prohibit unbounded buffering.
- [ ] Specify retry storms/circuit-breaker behavior when shared dependencies fail.
- [ ] Define supported protocol/schema version ranges and explicit incompatible-version error codes.
- [ ] Prevent silent downgrade when a newer security requirement would be lost.
- [ ] Expose queue depth, rejection count, retry count, timeout count, and cancellation metrics.
- [ ] Add deterministic tests using fake clocks/fault injection for deadlines, retries, idempotent duplicates, cancellation races, overload, and version mismatch.
- [ ] Document client guidance for interpreting retryability and preserving idempotency across process restarts.

### Acceptance / closure criteria
- [ ] No operation can wait, retry, queue, or buffer without a documented bound.
- [ ] Duplicate state-changing requests produce one logical effect within the idempotency window.
- [ ] Unsupported peer versions fail explicitly rather than being misparsed or silently downgraded.
- [ ] Fault tests prove bounded recovery without retry amplification.

## MC-10 — Build adjacent-layer integration harnesses for INV-10, INV-63, INV-65, and INV-66

**Severity:** Critical
**Traceability:** C030, C083
**Objective:** Prove application-model interoperability with every declared adjacent architecture layer using deterministic fixtures and executable end-to-end contracts.

### Required deliverables
- [ ] Create an integration test topology that instantiates or emulates INV-10, INV-63, INV-65, and INV-66 interfaces.
- [ ] Create versioned fixtures covering valid topology, invalid references, provider bindings, capability constraints, and deployment-manager/control-plane handoff.
- [ ] Add a test harness with deterministic startup, health probes, teardown, log capture, and machine-readable results.
- [ ] Add compatibility scenarios for the minimum/current supported version of each adjacent component.
- [ ] Run the harness in CI and production-release certification.

### Engineering / implementation checklist
- [ ] Define the exact contract boundary and responsibility split with each adjacent INV component.
- [ ] Verify schema/IDL compatibility and peer-version negotiation before executing semantic tests.
- [ ] Test happy-path submission through validation/canonicalization into adjacent-layer consumption.
- [ ] Test rejection propagation and stable error mapping across layer boundaries.
- [ ] Test unavailable/slow/malformed adjacent services and confirm deadlines/backpressure semantics from MC-09.
- [ ] Test provider/capability resolution failures and ensure no partial activation occurs.
- [ ] Verify correlation IDs and trace context propagate end-to-end.
- [ ] Verify tenant identity and authorization context cannot be dropped or replaced at handoff.
- [ ] Capture component versions, fixture digests, logs, traces, and results in release evidence.
- [ ] Keep synthetic emulators separate from at least one certification profile using the real adjacent implementations.

### Acceptance / closure criteria
- [ ] Each declared adjacent layer has at least one positive and multiple negative end-to-end tests.
- [ ] Production CI contains a non-optional integration stage with no unexpected skips.
- [ ] Version incompatibility and dependency outages produce deterministic gate failures.
- [ ] Release evidence identifies the exact adjacent component versions tested.

## MC-11 — Pin the exact approved OAM specification/implementation version

**Severity:** High
**Traceability:** C031, C093
**Objective:** Remove ambiguity around the Open Application Model reference point and define exactly which version/commit/profile INV-64 implements or borrows semantics from.

### Required deliverables
- [ ] Select the normative OAM specification/implementation reference and record an immutable version/tag/commit/digest.
- [ ] Document which OAM concepts are adopted, adapted, or intentionally unsupported by INV-64.
- [ ] Add a compatibility/profile document mapping INV-64 schema fields and semantics to the pinned OAM reference.
- [ ] Add change-review procedure for upgrading the OAM baseline.
- [ ] Include the OAM baseline version in machine-readable release metadata.

### Engineering / implementation checklist
- [ ] Do not reference an unpinned branch, mutable web page, or generic 'OAM' label as normative evidence.
- [ ] Capture the source URL/repository, commit/tag, content digest, license, and retrieval date.
- [ ] Identify deviations from OAM behavior and explain why they are safe/intentional.
- [ ] Define whether OAM compatibility is source-level, schema-level, semantic, or conceptual only.
- [ ] Create conformance fixtures for all OAM-compatible constructs claimed by the repository.
- [ ] Create negative fixtures for unsupported constructs so rejection behavior is explicit.
- [ ] Assess security/compatibility changes before any baseline upgrade.
- [ ] Update MC-30 compatibility matrix with OAM baseline relationships.
- [ ] Archive the prior baseline and migration notes when upgrading.
- [ ] Verify documentation and package metadata show the same baseline.

### Acceptance / closure criteria
- [ ] An auditor can identify one exact OAM reference and reproduce its content digest.
- [ ] All claimed OAM compatibility statements are backed by a mapping and tests.
- [ ] Baseline drift causes a review/gate event rather than silently changing semantics.

## MC-12 — Implement site/environment overlays and configuration provenance

**Severity:** High
**Traceability:** C035-C036
**Objective:** Allow environment-specific configuration without rebuilding immutable code while preserving deterministic merge semantics and full provenance.

### Required deliverables
- [ ] Define a versioned overlay schema distinct from the immutable application manifest/artifact.
- [ ] Define deterministic overlay precedence and merge semantics, including deletion/override rules.
- [ ] Record configuration ID/version, source digest, author/actor, approval, target scope, creation time, activation time, and parent/base revision.
- [ ] Implement validation of base-plus-overlay effective configuration before activation.
- [ ] Expose the effective configuration digest and provenance through status/diagnostics.

### Engineering / implementation checklist
- [ ] Define allowed overlay fields and prohibit overlays from mutating immutable identity/security-critical fields unless explicitly authorized.
- [ ] Scope overlays by tenant/environment/site and reject cross-scope application.
- [ ] Make merge order deterministic and canonicalizable; identical inputs must produce the same effective digest.
- [ ] Detect conflicting overlays and fail rather than selecting by filesystem/listing order.
- [ ] Store provenance in append-only or versioned configuration history.
- [ ] Support dry-run/diff showing effective changes before activation.
- [ ] Integrate secret-reference policy from MC-14 rather than embedding secret values.
- [ ] Add tests for missing base, stale parent revision, conflicting overlays, invalid scope, unauthorized author, and deterministic replay.
- [ ] Provide export/import of effective non-secret configuration for incident reconstruction.
- [ ] Link every activated configuration revision to the release/artifact version it targets.

### Acceptance / closure criteria
- [ ] Site/environment changes do not require rebuilding the immutable package/artifact.
- [ ] Effective configuration is reproducible from versioned base + ordered overlays.
- [ ] Every activation has attributable provenance and a stable digest.
- [ ] Unauthorized or ambiguous overlay changes fail closed before activation.

## MC-13 — Add atomic configuration activation and tested automatic/operator rollback

**Severity:** High
**Traceability:** C037-C038, C092
**Objective:** Prevent partial configuration state and guarantee a deterministic recovery path when activation fails or degrades service.

### Required deliverables
- [ ] Define an activation transaction model with prepare/validate/commit/abort phases or equivalent atomic primitive.
- [ ] Persist pre-activation revision/digest and activation transaction ID.
- [ ] Implement automatic rollback triggers for validation failure, health/readiness regression, or timed canary failure.
- [ ] Implement explicit operator rollback to a known-good revision.
- [ ] Add crash/restart recovery for interrupted activation transactions.

### Engineering / implementation checklist
- [ ] Specify atomicity boundary: single process, node, site, tenant, or fleet; document limits explicitly.
- [ ] Validate all security-critical and schema constraints before commit.
- [ ] Use compare-and-swap/revision preconditions to prevent lost updates and stale rollback.
- [ ] Ensure rollback itself is idempotent and cannot reapply an unsafe superseded revision accidentally.
- [ ] Define maximum activation and rollback deadlines with clear terminal outcomes.
- [ ] Quarantine failed candidate revisions and require explicit re-approval before retry.
- [ ] Record activation/rollback audit events including actor, from/to revisions, reason, and health evidence.
- [ ] Test process crash at every transaction phase, disk/full-store errors if persistence is used, duplicate commit/abort, concurrent activations, and stale writers.
- [ ] Integrate canary/staged rollout criteria from MC-40.
- [ ] Expose current, previous-known-good, pending, and failed revision status.

### Acceptance / closure criteria
- [ ] No failure test leaves an observably half-applied configuration within the documented atomicity scope.
- [ ] Automatic and manual rollback are exercised in CI or a release drill and produce evidence.
- [ ] Restart after an interrupted activation converges to one documented terminal state.
- [ ] Production gate verifies rollback readiness before release.

## MC-14 — Enforce secret-material exclusion and diagnostic redaction

**Severity:** Critical
**Traceability:** C039, C075
**Objective:** Prevent credentials, private keys, tokens, and sensitive tenant material from entering ordinary manifests, extension fields, logs, diagnostics, or evidence bundles.

### Required deliverables
- [ ] Create a secret-handling policy defining prohibited inline secret classes and approved secret-reference mechanisms.
- [ ] Add schema/semantic validation rules for known secret-bearing fields and extension namespaces.
- [ ] Implement centralized redaction/sanitization for logs, errors, diagnostics, traces, audit metadata, and support bundles.
- [ ] Add secret scanning in CI and release artifact generation.
- [ ] Create negative fixtures containing representative tokens/keys/passwords to prove rejection/redaction.

### Engineering / implementation checklist
- [ ] Define opaque secret reference format containing provider/key identifier and optional version, never plaintext secret value.
- [ ] Prevent error messages from echoing raw manifest fragments when those fragments may contain sensitive values.
- [ ] Classify high-cardinality diagnostic fields and apply allowlist-based export rather than blacklist-only redaction.
- [ ] Redact bearer tokens, API keys, PEM private keys, connection strings, passwords, cloud credentials, signed URLs, and common credential formats.
- [ ] Ensure canonical manifest digest policy is explicit for secret references; never hash secret plaintext that should not be present.
- [ ] Add entropy/pattern-based CI scanning with reviewed false-positive suppression.
- [ ] Test nested extension objects/arrays, Unicode obfuscation, alternate casing, percent/base64-encoded secrets, and exception stack traces.
- [ ] Define secure handling and retention for any unavoidable sensitive evidence.
- [ ] Add a break-glass diagnostic mode only if necessary, with elevated authorization, explicit consent, audit, and automatic expiry.
- [ ] Document operator remediation if a secret is accidentally committed or emitted, including rotation.

### Acceptance / closure criteria
- [ ] Representative secrets cannot be accepted in prohibited configuration locations.
- [ ] Known secret test values never appear in logs, traces, audit/evidence outputs, or support bundles.
- [ ] Secret references remain resolvable only by authorized runtime integration, not the pure parser.
- [ ] CI fails on committed/generated secret material according to policy.

## MC-15 — Implement artifact signature, digest, provenance, and approved-version verification pipeline

**Severity:** Critical
**Traceability:** C045
**Objective:** Verify every executable, policy, schema, or other trusted artifact consumed by INV-64 before use, and bind that verification to approved provenance/version policy.

### Required deliverables
- [ ] Define an artifact trust policy listing artifact classes, required digest/signature type, trusted signer/issuer, provenance level, and allowed versions.
- [ ] Implement verification before artifact activation/consumption.
- [ ] Require immutable cryptographic digests and reject digest/signature mismatches.
- [ ] Verify provenance attestations and builder/source identity where available.
- [ ] Emit verification results into machine-readable acceptance evidence.

### Engineering / implementation checklist
- [ ] Choose approved signature/attestation formats and algorithms; document algorithm agility and deprecation policy.
- [ ] Pin or trust-anchor signer identities independently of artifact-supplied metadata.
- [ ] Verify signature validity, certificate/key status, subject/issuer constraints, digest binding, and timestamp/expiry policy.
- [ ] Verify provenance subject digest matches the actual artifact and expected source/build workflow.
- [ ] Apply allow/deny policy to artifact version, source repository, branch/tag, builder, and dependency provenance as required.
- [ ] Define offline/cache behavior and fail-closed versus grace-period semantics when transparency/provenance services are unavailable.
- [ ] Protect against substitution/downgrade to a previously valid but no-longer-approved artifact.
- [ ] Add negative tests for tampered artifact, wrong signer, expired/revoked signer, mismatched provenance subject, unapproved version, and missing attestation.
- [ ] Record verification tool version and trust-policy version in evidence.
- [ ] Integrate generated release artifacts from MC-39 so producer and consumer controls are mutually testable.

### Acceptance / closure criteria
- [ ] No protected artifact is consumed before verification succeeds under the active trust policy.
- [ ] Tampering, signer mismatch, provenance mismatch, or unapproved version blocks activation.
- [ ] Verification evidence is attributable, reproducible, and linked to the exact artifact digest.
- [ ] Trust policy updates are versioned, authorized, auditable, and rollback-capable.

## MC-16 — Enforce tenant/workload isolation at integration/runtime boundaries

**Severity:** Critical
**Traceability:** C046
**Objective:** Convert documented tenant/workload boundaries into enforceable isolation for identity, memory/state, network, provider access, and diagnostics.

### Required deliverables
- [ ] Create an isolation architecture mapping tenant/workload identifiers to every runtime and data boundary.
- [ ] Implement tenant-scoped namespace/resource lookup and deny cross-tenant references by default.
- [ ] Define provider/network/device capability isolation and enforcement points.
- [ ] Partition mutable state, caches, queues, and telemetry where shared structures could leak or interfere across tenants.
- [ ] Add adversarial cross-tenant isolation tests.

### Engineering / implementation checklist
- [ ] Bind tenant/workload scope to authenticated identity and authorization context rather than trusting manifest-provided scope alone.
- [ ] Prevent cross-tenant component/provider/link references unless an explicit shared-resource contract exists.
- [ ] Apply memory/process/container/WASM isolation appropriate to the integration runtime and document residual shared-kernel risks.
- [ ] Enforce tenant-aware rate/resource limits to prevent noisy-neighbor starvation.
- [ ] Ensure cache keys and idempotency keys include tenant scope where required.
- [ ] Segment logs/traces/diagnostics and restrict operator views according to authorization.
- [ ] Prevent tenant-controlled identifiers from altering filesystem paths, metric labels, or provider endpoints without validation.
- [ ] Test identifier collision, confused deputy, cache poisoning, cross-tenant replay, shared-provider misuse, and diagnostic data exfiltration.
- [ ] Define isolation behavior during failover/recovery so state is not restored into the wrong tenant scope.
- [ ] Document any intentionally shared resource and its fairness/security policy.

### Acceptance / closure criteria
- [ ] Automated tests fail any attempt to read, mutate, reference, or infer another tenant's protected resources without explicit authorization.
- [ ] Isolation controls remain effective during retry, rollback, failover, and diagnostics.
- [ ] Production evidence identifies the isolation profile/runtime used for certification.

## MC-17 — Implement transport/storage encryption, managed key rotation, and trust-service outage behavior

**Severity:** Critical
**Traceability:** C047-C048
**Objective:** Protect sensitive data in transit and at rest while defining safe, testable behavior for identity/key/policy/time-service outages.

### Required deliverables
- [ ] Classify INV-64 data by sensitivity and identify every transit and storage path requiring encryption.
- [ ] Require modern authenticated encryption/TLS settings for network boundaries and approved encryption for persistent sensitive state/evidence.
- [ ] Integrate managed key identifiers rather than embedding key material in configuration.
- [ ] Define key rotation, revocation, compromise recovery, and backward-decryption windows.
- [ ] Define explicit fail-open/fail-closed/degraded behavior for identity, attestation, policy, key, and trusted-time service outages.

### Engineering / implementation checklist
- [ ] Specify minimum protocol/cipher/key sizes and disable insecure fallback/downgrade.
- [ ] Authenticate peers as part of transport security where boundary requirements demand it.
- [ ] Separate data-encryption keys from key-encryption/trust roots and restrict key-use permissions.
- [ ] Record key version/ID in encrypted-object metadata without exposing key material.
- [ ] Test rotation while reads/writes/activations are in flight.
- [ ] Test revoked/disabled key behavior and recovery from partial rotation.
- [ ] Define cached-trust validity windows for transient service outages and prohibit creation of new unverifiable trust beyond policy.
- [ ] Handle trusted-clock uncertainty explicitly for certificate/token expiry and provenance timestamp checks.
- [ ] Emit metrics/alerts for cryptographic verification failures and trust-service unavailability.
- [ ] Document emergency key compromise procedure and required artifact/config re-sign/re-encryption steps.

### Acceptance / closure criteria
- [ ] Sensitive in-scope data is never transmitted or persisted in plaintext across protected boundaries.
- [ ] Key rotation is tested without data loss or indefinite use of retired keys.
- [ ] Outage tests demonstrate the documented trust-service behavior and prevent unsafe implicit fail-open.
- [ ] Cryptographic configuration and key IDs are auditable without exposing secrets.

## MC-18 — Add tamper-evident security audit event emitter/ledger

**Severity:** Critical
**Traceability:** C049, C090
**Objective:** Produce append-only, verifiable audit records for security-sensitive operations with integrity chaining and evidence retention suitable for incident reconstruction and certification.

### Required deliverables
- [ ] Define a versioned audit event schema with event ID, timestamp, actor, tenant, operation, resource, outcome, reason, policy/config/release versions, correlation ID, and integrity fields.
- [ ] Implement audit emission for authentication, authorization, submission, validation rejection, activation, rollback, policy change, artifact verification, break-glass, and administrative operations.
- [ ] Implement tamper evidence using hash chaining, signed batches, append-only external store, or an approved equivalent.
- [ ] Add verifier tooling that detects deletion, insertion, reordering, or mutation according to the chosen integrity scheme.
- [ ] Include audit-integrity verification in release/acceptance evidence where applicable.

### Engineering / implementation checklist
- [ ] Define clock source/ordering semantics and behavior when trusted time is unavailable.
- [ ] Ensure failed/denied operations are audited where security-relevant, not only successes.
- [ ] Do not log credentials, secret values, or unnecessary sensitive payloads; integrate MC-14 redaction.
- [ ] Protect audit write path from tenant-controlled blocking or log injection.
- [ ] Define local buffering bounds and loss behavior when the audit sink is unavailable; surface dropped-event counters as critical alerts.
- [ ] Define retention, immutability, access controls, and export process.
- [ ] Add chain checkpointing/sealing strategy so compromise of a current process cannot silently rewrite all history.
- [ ] Add tests for record mutation, truncation, gap, duplicate, reorder, invalid signature, sink outage, queue overflow, and restart continuity.
- [ ] Correlate audit records to release/configuration/artifact digests.
- [ ] Provide an operator/auditor verification command producing machine-readable result.

### Acceptance / closure criteria
- [ ] All defined security-sensitive operations emit audit events with stable schema.
- [ ] Tampering with stored audit records is detected by the verifier.
- [ ] Audit sink outage cannot silently discard unlimited events; bounded-loss behavior is visible and alerts.
- [ ] A release/incident can be reconstructed from verified audit events without access to secrets.

## MC-19 — Add fuzzing, property-based, parser-differential, and adversarial resource-exhaustion suites

**Severity:** High
**Traceability:** C050, C085, C087
**Objective:** Systematically test hostile and malformed inputs beyond hand-written fixtures, including parser ambiguity and bounded-resource behavior.

### Required deliverables
- [ ] Add property-based generators for valid and invalid application manifests.
- [ ] Add coverage-guided or mutation fuzz harnesses around raw JSON parse, semantic validation, canonicalization, and any protocol/WIT/RPC decoders.
- [ ] Add parser-differential tests comparing accepted/rejected/canonical interpretations across selected JSON/schema implementations where relevant.
- [ ] Add adversarial resource-exhaustion corpus and time/memory budgets.
- [ ] Persist minimized regression inputs for every discovered failure.

### Engineering / implementation checklist
- [ ] Define invariants: parse/canonicalization never executes input, canonicalization is deterministic, valid canonical output revalidates, invalid input never obtains identity, no duplicate-key ambiguity, and caller input is not mutated.
- [ ] Generate deeply nested, wide, long-string, Unicode edge, duplicate-key, numeric-boundary, non-finite, encoding-invalid, and reference-graph edge cases.
- [ ] Test near-limit and over-limit payload/list sizes and ensure rejection cost remains bounded.
- [ ] Test algorithmic complexity attacks against duplicate/reference validation and canonical sorting.
- [ ] Test malformed schema versions and extension namespaces.
- [ ] Fuzz every machine-readable boundary added by MC-06, not only `manifest.py`.
- [ ] Use reproducible seeds and archive failing corpus digests.
- [ ] Run a fast fuzz smoke budget in normal CI and a longer scheduled/release campaign separately.
- [ ] Track coverage and unique crash/hang/assertion outcomes; fail on any unexpected exception or budget violation.
- [ ] Integrate threat-model-derived payloads, including credential-like data to exercise MC-14 redaction/rejection.

### Acceptance / closure criteria
- [ ] No unreproduced crash, hang, unbounded memory growth, parser disagreement affecting security semantics, or invariant violation remains open at release.
- [ ] Fuzz campaigns emit seed, duration/iterations, code revision, corpus digest, coverage summary, and findings.
- [ ] Every resolved fuzz defect becomes a deterministic regression test.

## MC-20 — Define complete failure model and prove recovery with fault injection

**Severity:** High
**Traceability:** C051-C060
**Objective:** Specify failure domains and recovery semantics for dependencies, stalls, failover, degraded operation, replay, restart, partitions, split-brain, quarantine, and unsafe behavior.

### Required deliverables
- [ ] Create a failure-mode and effects analysis (FMEA) covering parser, integration dependencies, config store, identity/policy/key services, provider resolution, audit sink, network, host/process, and adjacent control planes.
- [ ] Define health/stall detection thresholds and ownership for every dependency.
- [ ] Define degraded-mode capabilities and explicit unsafe operations that must be blocked.
- [ ] Define restart/replay/idempotency semantics and split-brain/leader or writer-conflict behavior where applicable.
- [ ] Build a fault-injection harness and scenario catalog with measurable recovery objectives.

### Engineering / implementation checklist
- [ ] For each failure mode record detection signal, user-visible outcome, retryability, containment boundary, recovery action, RTO/RPO or equivalent, and escalation.
- [ ] Inject latency, timeout, connection reset, malformed response, dependency crash, process kill, storage error, stale data, policy/key service outage, and clock skew where applicable.
- [ ] Test dependency recovery while requests are in flight and verify no duplicate/partial activation.
- [ ] Test repeated crash loops and ensure quarantine/freeze/disable controls engage according to policy.
- [ ] Define and test replay ordering and duplicate suppression after restart.
- [ ] Test partition and reconnect behavior including divergent configuration versions.
- [ ] If distributed writers exist, define fencing/epoch/revision rules preventing split-brain commits.
- [ ] Expose failure/degraded state through MC-23 status and MC-24 telemetry.
- [ ] Record fault scenario ID, injected fault, timeline, observed behavior, recovery time, and pass/fail evidence.
- [ ] Add release-blocking thresholds for recovery objectives.

### Acceptance / closure criteria
- [ ] Every high-impact failure mode has a documented containment/recovery path and at least one executable fault test.
- [ ] Recovery tests meet defined objectives without silent data/config divergence or cross-tenant impact.
- [ ] Unsafe conditions trigger quarantine/disable rather than continued ambiguous operation.
- [ ] Fault-injection evidence is included in production certification.

## MC-21 — Establish reproducible performance, resource, and power baselines

**Severity:** High
**Traceability:** C061-C064, C068
**Objective:** Quantify latency, throughput, startup, CPU, memory, storage, network, and edge-power overhead under controlled, reproducible workloads.

### Required deliverables
- [ ] Create a benchmark specification defining hardware/VM profile, OS, Python/runtime versions, dataset/fixture sizes, warmup, repetitions, and statistical method.
- [ ] Implement benchmark harnesses for parse, validate, canonicalize, integration submission, and representative end-to-end flows.
- [ ] Measure p50/p95/p99/max latency and throughput across payload/component-count scales.
- [ ] Measure CPU, peak/resident memory, allocation growth, storage/network overhead, and startup/import costs.
- [ ] Where edge targets are relevant, capture power/thermal behavior using a documented measurement method.

### Engineering / implementation checklist
- [ ] Separate cold-start from warmed steady-state results.
- [ ] Benchmark valid and representative invalid manifests because error aggregation may have different cost.
- [ ] Test steady load, burst, overload, scale-out, scale-in, and post-fault recovery workloads.
- [ ] Measure per-tenant/per-workload overhead and high-cardinality fairness effects where integration tier is included.
- [ ] Define explicit SLO/threshold targets for p50/p95/p99/worst-case rather than only descriptive numbers.
- [ ] Use stable benchmark fixture digests and record all environment variables/CPU governor/container limits affecting results.
- [ ] Report confidence intervals or run-to-run variance and flag noisy benchmark environments.
- [ ] Store machine-readable raw results plus summarized trends.
- [ ] Compare against the prior approved release on equivalent environment.
- [ ] Document when a benchmark is not applicable on a platform instead of fabricating cross-platform equivalence.

### Acceptance / closure criteria
- [ ] Benchmarks are reproducible within documented variance on the reference environment.
- [ ] Approved thresholds exist for every release-blocking metric.
- [ ] Results include enough environment metadata to distinguish code regressions from hardware/runtime changes.
- [ ] Edge power/thermal metrics are either measured for declared edge profiles or explicitly marked non-applicable with approval.

## MC-22 — Analyze serialization/copy/hop costs, define capacity model, saturation signals, and performance-regression gate

**Severity:** High
**Traceability:** C065-C070
**Objective:** Translate raw benchmark data into architectural efficiency controls and automated release protection against resource or tail-latency regressions.

### Required deliverables
- [ ] Create a data-path diagram enumerating serialization boundaries, copies, context switches, network hops, cache layers, and duplicated state/images.
- [ ] Instrument bytes encoded/decoded, copy counts where measurable, hop count, queue depth, and per-stage latency.
- [ ] Define capacity equations/models for requests/sec, manifest size, concurrent tenants, queue depth, CPU, memory, and dependency throughput.
- [ ] Define saturation indicators and alert thresholds before catastrophic overload.
- [ ] Add a release gate comparing candidate performance to approved absolute and regression thresholds.

### Engineering / implementation checklist
- [ ] Profile canonicalization/validation hot paths and identify avoidable repeated decode/sort/copy work.
- [ ] Apply batching/caching/direct composition/zero-copy only when semantics and security isolation are preserved; document rejected optimizations.
- [ ] Bound memory, queue, concurrency, buffer size, fan-out, and cache growth with explicit limits.
- [ ] Model worst-case validation work for maximum allowed collections and error aggregation.
- [ ] Test capacity-model predictions against measured saturation points and update model parameters when they diverge.
- [ ] Define candidate-vs-baseline comparison rules, allowable variance, minimum sample count, and noisy-run retry policy.
- [ ] Gate startup/import time, density/memory, throughput, and tail latency at minimum.
- [ ] Record benchmark code revision and baseline release so historical comparisons remain valid.
- [ ] Emit regression evidence as machine-readable JSON suitable for MC-29/MC-37 gates.
- [ ] Require explicit approved waiver for a threshold regression, including business rationale and expiry.

### Acceptance / closure criteria
- [ ] Every material data-path overhead has measured evidence or an explicit rationale why measurement is not feasible.
- [ ] Capacity model predicts saturation within an agreed tolerance on reference workloads.
- [ ] Candidate releases that exceed configured regression/absolute thresholds fail CI/release certification.
- [ ] Resource bounds are enforced in code/config, not only documented.

## MC-23 — Expose health, readiness, version, configuration, dependency, and capability status

**Severity:** High
**Traceability:** C071
**Objective:** Provide a stable operational status surface that distinguishes liveness from readiness and identifies exact runtime/config/dependency state.

### Required deliverables
- [ ] Define a versioned status schema/API or command output.
- [ ] Expose component version/build digest, schema/spec version, active configuration revision/digest, and capability set.
- [ ] Expose dependency status for `pk_core`, adjacent layers, identity/policy/key/audit services as applicable.
- [ ] Define separate liveness, readiness, degraded, and blocked states with reason codes.
- [ ] Add status integration tests for healthy and failure scenarios.

### Engineering / implementation checklist
- [ ] Do not mark readiness true solely because the process/import is alive; verify required dependencies and active configuration validity.
- [ ] Include last-success/last-failure timestamps and bounded human-readable reason detail.
- [ ] Report stale/unknown dependency state distinctly from healthy.
- [ ] Expose current/previous/pending configuration revisions and activation state from MC-13.
- [ ] Expose trust-policy/OAM/contract version identifiers needed to diagnose compatibility.
- [ ] Protect sensitive fields and tenant-specific detail through authorization/redaction.
- [ ] Ensure status evaluation itself is bounded and does not create dependency storms.
- [ ] Add negative tests for missing dependency, invalid config, policy/key outage, degraded mode, rollback in progress, and version mismatch.
- [ ] Map status reason codes to operator runbook sections.
- [ ] Export status in machine-readable form suitable for orchestration probes and certification evidence.

### Acceptance / closure criteria
- [ ] Operators can determine within one status query whether INV-64 is live, ready, degraded, or blocked and why.
- [ ] Status includes exact active versions/configuration/capabilities without secrets.
- [ ] Readiness transitions correctly under injected dependency/configuration failures.

## MC-24 — Implement metrics, structured logs, trace propagation, and safe diagnostics

**Severity:** High
**Traceability:** C072-C075
**Objective:** Provide actionable telemetry for rate/errors/latency/saturation/resources while preserving cross-service correlation and tenant/secret safety.

### Required deliverables
- [ ] Define a stable metric catalog with names, units, labels, cardinality policy, and SLO linkage.
- [ ] Define structured log schema with timestamp, severity, node, tenant, workload, component, operation, correlation/trace IDs, outcome, and stable error code.
- [ ] Propagate standard trace context across all relevant integration boundaries.
- [ ] Add bounded, authorization-aware diagnostic endpoints/commands.
- [ ] Implement redaction/cardinality controls integrated with MC-14.

### Engineering / implementation checklist
- [ ] Instrument request rate, success/rejection/error rate, validation/canonical latency, queue/backlog, saturation, retries/timeouts, dependency failures, and CPU/memory where integration layer permits.
- [ ] Avoid tenant/workload IDs as unbounded metric labels unless explicitly controlled; prefer logs/traces for high-cardinality detail.
- [ ] Use structured fields rather than parsing free-form text for operational automation.
- [ ] Propagate traceparent/tracestate or the selected standard and preserve correlation across retries/async work.
- [ ] Record policy/config/artifact/release version as low-cardinality or event attributes where useful.
- [ ] Sample traces according to MC-26 policy while retaining errors/security events at appropriate rates.
- [ ] Protect diagnostic endpoints with MC-07/MC-08 controls.
- [ ] Add telemetry self-health: exporter failures, dropped log/trace counters, queue saturation.
- [ ] Test redaction and cardinality limits with malicious identifiers and secret-like input.
- [ ] Create telemetry contract tests so field/metric changes are reviewed like API changes.

### Acceptance / closure criteria
- [ ] A representative request can be correlated across logs/traces and adjacent services without exposing secrets.
- [ ] Metrics support SLO/error-budget and saturation analysis.
- [ ] Telemetry failure is visible and bounded rather than silently consuming unbounded resources.
- [ ] Diagnostic outputs pass secret/redaction and authorization tests.

## MC-25 — Add decision explainability and release-lineage/infrastructure-graph correlation

**Severity:** Medium
**Traceability:** C076-C078
**Objective:** Make automated validation/selection/activation decisions explainable and correlate them to inputs, policy, topology, release lineage, and live infrastructure state.

### Required deliverables
- [ ] Define a versioned decision-record schema containing decision ID/type, outcome, reason codes, inputs/digests, policy/config version, candidate alternatives, and relevant constraints.
- [ ] Implement an operator-readable `explain` view over decision records.
- [ ] Correlate decisions to application release/artifact lineage and infrastructure/provider graph identifiers.
- [ ] Store sufficient non-secret input references to reproduce the decision.
- [ ] Add explainability contract tests.

### Engineering / implementation checklist
- [ ] Emit decision records for validation rejection, capability/provider resolution, policy rejection, activation/rollback, degraded-mode selection, and other automated choices made by the integration layer.
- [ ] Prefer stable reason codes plus bounded details rather than only natural-language explanations.
- [ ] Show which constraint dominated when multiple constraints conflict, using precedence rules from MC-05.
- [ ] Reference input/config/policy/artifact digests rather than duplicating sensitive payloads.
- [ ] Link release ID/build digest and infrastructure node/provider IDs to the same correlation chain.
- [ ] Define retention and access control for decision history.
- [ ] Handle missing/stale infrastructure-graph data explicitly in explanations.
- [ ] Test deterministic explanation fields for identical deterministic decisions.
- [ ] Ensure explain output is safe for multi-tenant operators and redacts unauthorized topology details.
- [ ] Document how operators use explanation data to distinguish invalid input, policy rejection, dependency failure, and software defect.

### Acceptance / closure criteria
- [ ] Every automated production-impacting decision has a retrievable reason record.
- [ ] Operators can trace a decision to exact release/config/policy/input and relevant infrastructure context.
- [ ] Explainability does not leak secrets or cross-tenant data.
- [ ] Reason codes remain stable/versioned and are included in test fixtures.

## MC-26 — Define telemetry retention/sampling/privacy/export policy, dashboards, and differentiated alerts

**Severity:** Medium
**Traceability:** C079-C080
**Objective:** Operationalize telemetry with explicit governance and dashboards/alerts that distinguish ordinary load, degradation, policy rejection, dependency failure, attack, and software defects.

### Required deliverables
- [ ] Create a telemetry governance policy covering data classes, retention, sampling, access, export destinations, residency/privacy constraints, and deletion.
- [ ] Define trace/log sampling rules including error/security-event exceptions.
- [ ] Build dashboards for golden signals, dependencies, validation outcomes, capacity/saturation, release/config state, and tenant-safe breakdowns.
- [ ] Define alert rules with severity, threshold/window, deduplication, owner, routing, and runbook link.
- [ ] Add alert testing/simulation and dashboard-as-code validation.

### Engineering / implementation checklist
- [ ] Classify telemetry fields as public/internal/sensitive/secret-prohibited and document export restrictions.
- [ ] Ensure retention differs appropriately between high-volume diagnostics and security/audit evidence.
- [ ] Define sampling that preserves rare errors and security signals without retaining prohibited payload data.
- [ ] Build alert logic to distinguish overload from dependency outage, policy rejection spikes, auth failures/attack patterns, and code exception regressions.
- [ ] Use multi-window/burn-rate alerts for SLOs where appropriate rather than static single-threshold noise.
- [ ] Link every actionable alert to an owner and MC-33/MC-34 runbook/procedure.
- [ ] Define maintenance/suppression rules with audit and expiry to prevent permanent alert muting.
- [ ] Test exporter outage, missing-series conditions, alert routing, and alert recovery/auto-close behavior.
- [ ] Version dashboards and alert rules in source control.
- [ ] Review privacy/residency implications of external telemetry providers.

### Acceptance / closure criteria
- [ ] Dashboards expose enough information to classify the major failure/attack/load categories required by C080.
- [ ] Critical alert paths are tested end-to-end and reach the documented escalation destination.
- [ ] Telemetry storage/export behavior complies with the documented privacy/retention policy.
- [ ] Alert and dashboard definitions are versioned and reproducible.

## MC-27 — Create cross-platform/runtime/provider/protocol compatibility matrix and tests

**Severity:** High
**Traceability:** C084
**Objective:** Define exactly which architectures, OS/Python runtimes, integration runtimes, providers, adjacent versions, and protocol/schema versions are supported and continuously test representative combinations.

### Required deliverables
- [ ] Create a machine-readable compatibility matrix with dimensions for CPU architecture, OS, Python, `pk_core`, OAM baseline, adjacent INV components, providers, and protocol/schema versions.
- [ ] Classify combinations as required, supported, experimental, deprecated, or unsupported.
- [ ] Add CI matrix jobs for all required combinations and representative supported combinations.
- [ ] Add compatibility fixtures for minimum/current peer protocol and schema versions.
- [ ] Publish the tested matrix with each release.

### Engineering / implementation checklist
- [ ] Include at least the platforms actually claimed by packaging/README/support policy; remove unsupported claims that are not tested.
- [ ] Test architecture-sensitive behavior such as integer/float canonicalization assumptions, path/encoding differences, and endian-independent digests.
- [ ] Test Windows and POSIX path/environment bootstrap where both are supported.
- [ ] Test min/max Python versions and min/max supported `pk_core`/adjacent versions.
- [ ] Exercise provider implementations or certified stubs according to support tier.
- [ ] Test forward/backward protocol/schema compatibility and explicit rejection outside supported ranges.
- [ ] Track flaky/inconclusive combinations separately; do not count skipped matrix jobs as support evidence.
- [ ] Record toolchain/runtime image digests for reproducibility.
- [ ] Define removal/deprecation timeline when a matrix row is dropped.
- [ ] Link compatibility failures to MC-30 matrix and MC-31 support/EOL policy.

### Acceptance / closure criteria
- [ ] Every 'required' matrix cell passes automated certification with no unexpected skips.
- [ ] Release notes identify added/removed/deprecated compatibility rows.
- [ ] Unsupported combinations fail with clear preflight diagnostics rather than undefined behavior.
- [ ] Compatibility evidence is machine-readable and attached to the release gate.

## MC-28 — Add concurrency/race, soak/burst/fleet-scale, and disaster/partition/reconnect suites

**Severity:** High
**Traceability:** C086, C088-C089
**Objective:** Validate correctness and operational behavior under concurrency, long duration, burst/overload, large fleets, and distributed failure/recovery scenarios.

### Required deliverables
- [ ] Create deterministic concurrency tests for shared state/config activation/idempotency/audit queues and integration caches.
- [ ] Add stress/soak/burst load profiles with controlled duration, request mix, tenant count, and resource limits.
- [ ] Add fleet-scale scenarios exercising many manifests/nodes/providers within documented capacity assumptions.
- [ ] Add disaster/partition/reconnect/degraded-control-plane scenarios.
- [ ] Automate leak/race/error-rate/resource-drift detection and evidence capture.

### Engineering / implementation checklist
- [ ] Test concurrent validate/canonicalize calls for thread/process safety and caller-input immutability.
- [ ] Test concurrent activation attempts, stale revisions, rollback races, duplicate idempotency keys, and audit emission ordering.
- [ ] Use race detectors/instrumentation where the selected runtime/language supports them; otherwise create schedule-stress and invariant checks.
- [ ] Measure memory/file-descriptor/thread/task/queue growth over long soak periods.
- [ ] Burst beyond capacity and verify bounded rejection/backpressure rather than collapse/unbounded queues.
- [ ] Partition control-plane/dependency links, perform divergent updates where possible, reconnect, and verify deterministic reconciliation/precedence.
- [ ] Restart components during load and verify retry/idempotency semantics prevent duplicate effects.
- [ ] Test disaster recovery from loss/corruption of reconstructible local state according to MC-32.
- [ ] Verify telemetry/alerts remain useful under high load and do not become the dominant failure source.
- [ ] Archive scenario configs, seeds, environment metadata, and raw results.

### Acceptance / closure criteria
- [ ] No race/invariant violation, unbounded resource growth, duplicate activation, or cross-tenant leakage is observed in required profiles.
- [ ] Soak/burst/fleet workloads meet defined error/latency/recovery objectives.
- [ ] Partition/reconnect tests converge to the documented state without silent divergence.
- [ ] Required stress/disaster suites are release-gated or have an explicitly scheduled certification cadence.

## MC-29 — Create local machine-readable acceptance evidence and formal production exit-gate artifact

**Severity:** Critical
**Traceability:** C090, C100
**Objective:** Make production certification self-describing, reproducible, and fail-closed through a local gate that aggregates architecture, security, resilience, performance, observability, testing, rollback, and ownership evidence.

### Required deliverables
- [ ] Define a versioned acceptance-evidence JSON schema.
- [ ] Implement a local gate command/script that evaluates all required controls and emits a single verdict plus per-control results.
- [ ] Include source revision, package/artifact digests, dependency versions, environment, tool versions, timestamps, and evidence references.
- [ ] Define verdict semantics such as GO/NO_GO/CONDITIONAL_GO with strict rules for blockers and waivers.
- [ ] Generate a signed/checksummed gate artifact for every release candidate.

### Engineering / implementation checklist
- [ ] Map every required `INV-64-C###` control to evidence state: pass/fail/not-applicable/waived, with reason and artifact reference.
- [ ] Reject missing evidence for Critical/High required controls rather than treating absence as success.
- [ ] Verify referenced evidence files exist and match recorded digests.
- [ ] Validate that tests had no unexpected skips and that required matrix/fault/performance jobs passed.
- [ ] Validate ownership/ADR, compatibility, rollback drill, vulnerability status, SBOM/signature/provenance, and operational runbook evidence.
- [ ] Include waiver IDs, approvers, compensating controls, and expiry; expired waivers must force NO_GO.
- [ ] Make the gate deterministic for a fixed evidence bundle and policy version.
- [ ] Add schema validation and tests for malformed/forged/incomplete evidence.
- [ ] Integrate `pk_core` gate output if authoritative, but retain a repository-local wrapper/schema that can detect absent or incompatible external evidence.
- [ ] Archive the gate policy version used for each release.

### Acceptance / closure criteria
- [ ] A production candidate cannot be marked GO with missing Critical/High evidence unless explicitly permitted by approved policy/waiver semantics.
- [ ] The gate artifact can be validated offline against its schema and referenced digests.
- [ ] Running the gate twice on the same evidence/policy yields the same verdict.
- [ ] The release bundle contains the final acceptance artifact and integrity metadata.

## MC-30 — Maintain supported-version compatibility matrix

**Severity:** High
**Traceability:** C093
**Objective:** Define and publish the exact supported combinations of INV-64, schema, Python, `pk_core`, OAM baseline, adjacent components, providers, and relevant protocols.

### Required deliverables
- [ ] Create `COMPATIBILITY.md` plus a machine-readable `compatibility.json`/YAML source.
- [ ] Define minimum/current/maximum or range for each dependency/interface dimension.
- [ ] Record support state, first-supported release, deprecation date, EOL date, and known constraints per row/range.
- [ ] Link matrix rows to automated MC-27 test jobs.
- [ ] Validate package/dependency constraints against the same matrix in CI.

### Engineering / implementation checklist
- [ ] Avoid broad untested ranges; every supported range must have test evidence at representative boundaries.
- [ ] Define schema/application model compatibility independently from implementation package compatibility where necessary.
- [ ] Include adjacent INV-10/63/65/66 version relationships.
- [ ] Include OAM baseline and protocol/IDL versions.
- [ ] Define downgrade/upgrade/migration requirements for incompatible transitions.
- [ ] Mark experimental combinations clearly and exclude them from production certification unless policy permits.
- [ ] Automate checks that README/pyproject/CI matrix do not contradict compatibility metadata.
- [ ] Publish matrix changes in release notes.
- [ ] Tie removed versions to MC-31 EOL policy.
- [ ] Retain historical matrices for audit of older releases.

### Acceptance / closure criteria
- [ ] Every production-supported combination is represented in machine-readable compatibility metadata and backed by tests.
- [ ] Package install/preflight rejects known-incompatible combinations.
- [ ] Documentation, CI, and runtime preflight derive from or validate against one compatibility source of truth.

## MC-31 — Define vulnerability response, patching, and end-of-life SLAs

**Severity:** High
**Traceability:** C094
**Objective:** Establish time-bounded processes for vulnerability intake, triage, remediation, disclosure, patch release, and dependency/runtime end-of-life.

### Required deliverables
- [ ] Create `SECURITY_RESPONSE.md` with vulnerability reporting channel and handling workflow.
- [ ] Define severity taxonomy and remediation/mitigation SLAs by severity.
- [ ] Define dependency/security advisory monitoring and patch intake process.
- [ ] Define supported release branches and EOL policy/timeline.
- [ ] Define emergency patch and release-signing/provenance requirements.

### Engineering / implementation checklist
- [ ] Document private triage and embargo handling where appropriate.
- [ ] Define severity calculation source/rules and who can override severity with rationale.
- [ ] Specify response targets for acknowledge, triage, mitigation, fix availability, and customer/operator communication.
- [ ] Include vulnerabilities in `pk_core`, Python, build tooling, OAM/IDL tooling, adjacent components, and transitive dependencies.
- [ ] Automate dependency/advisory scanning in CI/release workflow with policy thresholds.
- [ ] Define exception process when a fix cannot meet SLA, including compensating controls and expiry.
- [ ] Specify when a vulnerable release is revoked or blocked by artifact trust policy.
- [ ] Define EOL notice period and post-EOL vulnerability handling.
- [ ] Link compatibility matrix states to supported/EOL branch policy.
- [ ] Practice at least one tabletop/emergency patch drill and capture findings.

### Acceptance / closure criteria
- [ ] Severity-to-response timelines are explicit and owned.
- [ ] Supported release lines receive security updates according to documented SLA.
- [ ] Known policy-blocking vulnerabilities cause release-gate failure or an explicit approved exception.
- [ ] EOL status is visible in compatibility/release metadata.

## MC-32 — Define backup, restore, migration, and reconstruction applicability/procedures

**Severity:** Medium
**Traceability:** C095
**Objective:** Determine which INV-64 state is authoritative, derived, ephemeral, or externally owned and provide tested recovery/migration procedures for every persistent element.

### Required deliverables
- [ ] Create a state inventory classifying manifests, configuration history, evidence, audit records, caches, indexes, and integration state by source of truth and persistence.
- [ ] For each state class, declare backup requirement or explicit reconstructible/non-applicable rationale.
- [ ] Define restore/reconstruction procedure with integrity validation and tenant/environment scoping.
- [ ] Define schema/config migration procedure across supported versions.
- [ ] Add recovery tests and evidence.

### Engineering / implementation checklist
- [ ] Do not back up caches/derived state unnecessarily; document deterministic rebuild inputs instead.
- [ ] Define backup consistency/atomicity requirements relative to configuration activation transactions.
- [ ] Encrypt and access-control backups containing sensitive metadata.
- [ ] Record backup format/version and compatibility with software/schema versions.
- [ ] Verify restore into an isolated environment before declaring success.
- [ ] Check cryptographic digests/signatures and audit-chain continuity after restore where applicable.
- [ ] Define RPO/RTO targets for required persistent state.
- [ ] Test migration forward and rollback/backward path where supported; define irreversible migrations explicitly.
- [ ] Test missing/corrupt partial state and confirm reconstruction fails safely when authoritative inputs are unavailable.
- [ ] Document retention and secure deletion of retired backups.

### Acceptance / closure criteria
- [ ] Every persistent state class has a tested backup/restore or reconstruction decision.
- [ ] Restore/rebuild tests meet defined integrity and recovery objectives.
- [ ] Migration procedures are version-aware and prevent accidental use with incompatible binaries/schemas.
- [ ] Recovery evidence is linked to release/operations documentation.

## MC-33 — Create complete day-0, day-1, and day-2 operator runbooks

**Severity:** Medium
**Traceability:** C096
**Objective:** Turn the current outline into executable operational procedures covering bootstrap, deployment, validation, upgrades, routine operations, diagnosis, rollback, and decommissioning.

### Required deliverables
- [ ] Create separate Day-0 bootstrap, Day-1 deploy/upgrade, and Day-2 operate/troubleshoot runbooks.
- [ ] Include prerequisites, permissions, environment assumptions, exact commands, expected outputs, validation points, and rollback steps.
- [ ] Add Windows and POSIX variants where both are supported.
- [ ] Link status reason codes, alerts, and common errors to troubleshooting decision trees.
- [ ] Add runbook validation/drill evidence.

### Engineering / implementation checklist
- [ ] Day-0: provision runtime/dependencies, verify package/artifact integrity, configure trust roots, bootstrap `pk_core`, validate compatibility, and establish baseline evidence.
- [ ] Day-1: validate candidate config, dry-run/diff, canary/stage, observe gates, commit activation, verify readiness, and archive evidence.
- [ ] Day-2: routine health checks, SLO/error-budget review, configuration changes, dependency rotation, key/cert rotation, audit verification, and capacity review.
- [ ] Include rollback/emergency-disable/quarantine procedures with exact prerequisites and confirmation checks.
- [ ] Include diagnostics collection with MC-14 redaction and authorization requirements.
- [ ] Include dependency outage and degraded-mode decision paths.
- [ ] Include upgrade/migration/compatibility checks from MC-30/MC-32.
- [ ] Define safe stop/decommission procedure and evidence retention.
- [ ] State who is authorized to perform each risky action.
- [ ] Test runbooks periodically on a clean/recovery environment and incorporate operator feedback.

### Acceptance / closure criteria
- [ ] A qualified operator unfamiliar with local developer assumptions can bootstrap, deploy, verify, diagnose, rollback, and decommission using only the runbooks and approved credentials.
- [ ] Runbook commands match current package/tool syntax and are checked in CI where feasible.
- [ ] Critical procedures are exercised in drills with timestamps/results/lessons learned.

## MC-34 — Define incident severity, paging, escalation, containment, and recovery procedures

**Severity:** High
**Traceability:** C097
**Objective:** Provide a formal incident-management process specific to INV-64 failure and security scenarios.

### Required deliverables
- [ ] Create an incident response procedure with severity levels, examples, declaration authority, paging routes, and escalation timers.
- [ ] Define containment actions including freeze, rollback, disable, credential/key revocation, and provider isolation.
- [ ] Define recovery validation and criteria for returning to normal operation.
- [ ] Define evidence preservation and communication requirements.
- [ ] Link alert classes to incident severity/runbook entry points.

### Engineering / implementation checklist
- [ ] Include scenarios for widespread invalid deployments, auth/authz bypass, artifact/provenance compromise, key compromise, cross-tenant leakage, audit integrity failure, dependency outage, performance collapse, and bad configuration rollout.
- [ ] Define incident commander, operations, security, communications, and scribe roles.
- [ ] Record timeline in a standard incident log with correlation to audit/release/config digests.
- [ ] Preserve forensic evidence before destructive remediation when safe/required.
- [ ] Define customer/operator notification triggers and sensitive-disclosure handling.
- [ ] Define handoff/escalation to adjacent-component owners for INV-10/63/65/66 or `pk_core` faults.
- [ ] Require post-incident review for defined severities and track corrective actions to closure.
- [ ] Test contact/paging paths and break-glass access.
- [ ] Run tabletop exercises for at least one security and one availability incident.
- [ ] Ensure containment procedures have bounded blast radius and explicit recovery confirmation.

### Acceptance / closure criteria
- [ ] Critical alert simulations reach the correct on-call/escalation path.
- [ ] Tabletop/drill evidence shows the team can contain and recover using documented controls.
- [ ] Post-incident actions are assigned owners and deadlines and feed MC-36 debt/waiver tracking.
- [ ] Incident handling preserves audit/provenance evidence needed for root cause analysis.

## MC-35 — Establish recurring access, policy, dependency, configuration, and architecture reviews

**Severity:** Medium
**Traceability:** C098
**Objective:** Prevent control drift by scheduling and evidencing periodic reviews of security access, policies, dependencies, configuration, and architecture assumptions.

### Required deliverables
- [ ] Create a review calendar/cadence and owner for each required review domain.
- [ ] Create standardized review templates and evidence records.
- [ ] Automate data collection for identities/access, dependency versions/vulnerabilities, active configuration, policy versions, and compatibility status.
- [ ] Define findings severity, remediation tracking, and escalation for overdue actions.
- [ ] Include architecture/ADR revalidation at defined intervals and major-change triggers.

### Engineering / implementation checklist
- [ ] Access review: verify principals, roles/capabilities, tenant scopes, break-glass accounts, stale identities, and least privilege.
- [ ] Policy review: verify authz/trust/secret/telemetry/retention policies remain current and tested.
- [ ] Dependency review: verify supported versions, vulnerabilities, provenance, and upcoming EOL.
- [ ] Configuration review: compare active config to approved source, detect drift, stale overlays, expired exceptions, and unapproved changes.
- [ ] Architecture review: validate assumptions about adjacent layers, platform tiers, threat model, capacity, and OAM baseline.
- [ ] Trigger out-of-cycle review after major incident, trust-model change, new platform tier, new provider, or significant dependency upgrade.
- [ ] Record reviewer, date, scope, evidence digests, findings, and next due date.
- [ ] Prevent self-approval for high-risk access/policy changes where separation of duties is required.
- [ ] Feed findings into MC-36 register and MC-29 release gate when unresolved findings are release-blocking.
- [ ] Retain historical review evidence according to governance policy.

### Acceptance / closure criteria
- [ ] Every required review domain has a documented cadence, accountable reviewer, and most-recent evidence.
- [ ] Overdue Critical/High review findings are visible to the production gate.
- [ ] Configuration/access drift is detectable from review evidence rather than relying on manual recollection.

## MC-36 — Create exception/waiver/technical-debt/deprecation register

**Severity:** Medium
**Traceability:** C099
**Objective:** Make residual risk and planned removals explicit, owned, time-bounded, and visible to release governance.

### Required deliverables
- [ ] Create a machine-readable register for exceptions, waivers, technical debt, deprecated behaviors, and temporary compatibility bridges.
- [ ] Define required fields: ID, type, description, affected controls/components, risk, owner, approvers, compensating controls, created date, expiry/review date, status, and closure evidence.
- [ ] Integrate active/expired register entries into the production gate.
- [ ] Define deprecation announcement/removal workflow and compatibility impact assessment.
- [ ] Add automated expiry checks.

### Engineering / implementation checklist
- [ ] Disallow waivers without an accountable owner and explicit expiry/review date.
- [ ] Require higher-level/security approval for Critical security-control exceptions.
- [ ] Record why the requirement cannot be met now and what concrete work closes it.
- [ ] Define maximum waiver duration by severity and prohibit silent auto-renewal.
- [ ] Link compensating-control evidence and verify it remains effective during the waiver period.
- [ ] Track debt aging and repeated extensions as governance signals.
- [ ] For deprecated behavior, record first-deprecated version, warning behavior, replacement, final supported version, and removal version/date.
- [ ] Emit CI warnings/failures for expired entries.
- [ ] Include active production-impacting waivers in release notes/gate evidence as policy requires.
- [ ] Close entries only with evidence, not by deletion; preserve history.

### Acceptance / closure criteria
- [ ] No production exception exists outside the register.
- [ ] Expired Critical/High waivers block certification automatically.
- [ ] Every active entry has owner, expiry, compensating control, and closure plan.
- [ ] Historical entries remain auditable after closure.

## MC-37 — Add CI workflow for standalone, integration, security, compatibility, performance, and release gates

**Severity:** High
**Traceability:** C070, C081-C090, C100
**Objective:** Continuously enforce the repository's correctness and certification requirements in a reproducible pipeline where required external dependencies are present.

### Required deliverables
- [ ] Add a version-controlled CI workflow with stages for lint/static checks, standalone tests, package build/install, integration conformance, security/fuzz smoke, compatibility matrix, performance regression, and acceptance gate.
- [ ] Provide a CI environment/job where `pk_core` and required adjacent test dependencies are installed at pinned versions.
- [ ] Upload machine-readable evidence and logs for each stage.
- [ ] Make required stages branch/release protections rather than advisory jobs.
- [ ] Add scheduled extended fuzz/soak/disaster jobs where runtime is too high for every commit.

### Engineering / implementation checklist
- [ ] Fail on unexpected test skips, test discovery failure, import failure, or missing dependencies.
- [ ] Build wheel/sdist and test installed artifacts rather than only source-tree imports.
- [ ] Run `compileall` plus selected static/type/security tooling with pinned tool versions.
- [ ] Cache dependencies safely without allowing stale/unverified cache to bypass integrity checks.
- [ ] Use least-privilege CI credentials and isolate untrusted pull-request execution from release signing secrets.
- [ ] Generate SBOM/provenance/checksums/signatures in protected release jobs only.
- [ ] Run MC-27 matrix rows and MC-10 adjacent integration tests according to policy.
- [ ] Compare candidate benchmarks to approved baseline and fail configured regressions.
- [ ] Validate all generated JSON/schema/evidence artifacts and cross-file version consistency.
- [ ] End with MC-29 formal production gate and publish a single final verdict.

### Acceptance / closure criteria
- [ ] Required CI jobs are reproducible on clean runners and contain no hidden workstation dependency.
- [ ] A missing `pk_core`, failed integration, failed security test, performance regression, expired waiver, or invalid evidence causes a non-zero release-gate result.
- [ ] Release artifacts can be traced to one successful protected pipeline run and source revision.
- [ ] Scheduled extended tests produce retained results and open actionable failures.

## MC-38 — Add explicit distribution license, NOTICE, and SPDX metadata

**Severity:** Medium
**Traceability:** release/supply-chain hygiene
**Objective:** Make legal distribution terms and machine-readable licensing unambiguous for source and packaged artifacts.

### Required deliverables
- [ ] Select/confirm the project distribution license with authorized owner/legal approval.
- [ ] Add canonical `LICENSE` text and `NOTICE` where required by the selected license/dependencies.
- [ ] Add SPDX license identifier metadata to `pyproject.toml` and source headers where organizational policy requires it.
- [ ] Inventory third-party licenses and required attribution/notice obligations.
- [ ] Validate license metadata during packaging/release.

### Engineering / implementation checklist
- [ ] Ensure README license statement matches the actual license file and package metadata.
- [ ] Include license/notice files in wheel and sdist.
- [ ] Record licenses for `pk_core`, OAM reference materials, schemas/tooling, and any vendored fixtures/code.
- [ ] Avoid copying normative source material without documented redistribution rights.
- [ ] Generate third-party notice report from dependency/SBOM data where practical.
- [ ] Add automated license-policy scanning for incompatible/unknown dependency licenses.
- [ ] Define process for exceptions/manual license review.
- [ ] Include copyright holder/year information according to project policy.
- [ ] Verify generated artifacts do not strip required notices.
- [ ] Record license metadata in SBOM and provenance outputs.

### Acceptance / closure criteria
- [ ] Source and built distributions contain clear, consistent license/notice information.
- [ ] All shipped third-party components have known licenses and required notices.
- [ ] Unknown/disallowed license findings block release or have an approved exception.

## MC-39 — Generate SBOM, checksums, signatures, and release provenance artifacts

**Severity:** High
**Traceability:** C045, C090, supply-chain hygiene
**Objective:** Publish verifiable software-supply-chain metadata for each release so consumers can identify contents, integrity, origin, and build process.

### Required deliverables
- [ ] Generate an SBOM for source/build dependencies and packaged release contents using an approved machine-readable format.
- [ ] Generate SHA-256 or stronger checksums for every release artifact/evidence bundle.
- [ ] Sign release artifacts/checksum manifest using the approved signing mechanism.
- [ ] Generate build provenance attestation binding source revision, builder identity, workflow, dependencies, and artifact digests.
- [ ] Publish/retain these artifacts together with the release and acceptance evidence.

### Engineering / implementation checklist
- [ ] Ensure SBOM includes direct/transitive Python dependencies, vendored components, and build tooling where policy requires.
- [ ] Record package versions, purls/CPEs or equivalent identifiers, and license data where supported.
- [ ] Create a deterministic artifact manifest listing filename, media/type, size, digest, signature reference, SBOM subject relationship, and provenance reference.
- [ ] Protect signing keys using managed signing service/HSM/OIDC-keyless or equivalent; do not place private keys in repository/CI variables accessible to untrusted jobs.
- [ ] Sign only after all release gates pass and bind signature to final immutable digest.
- [ ] Test consumer-side verification in CI using the trust policy from MC-15.
- [ ] Scan SBOM against vulnerability policy and surface findings to MC-31/MC-29.
- [ ] Retain provenance and transparency/log references if used.
- [ ] Version the SBOM/provenance generation tools and capture their versions in evidence.
- [ ] Verify release upload/publishing process cannot substitute unsigned artifacts after signing.

### Acceptance / closure criteria
- [ ] Every production release artifact has a recorded digest, SBOM relationship, signature/verification path, and provenance attestation.
- [ ] Consumer verification tests reject tampered or unsigned artifacts according to policy.
- [ ] Supply-chain metadata references the same source revision and artifact digests as the production gate.
- [ ] Signing credentials are isolated from untrusted CI execution.

## MC-40 — Define canary/staged rollout and perform tested rollback drill

**Severity:** High
**Traceability:** C092
**Objective:** Reduce rollout blast radius by progressively exposing candidates to controlled scopes, evaluating health/SLO/security gates, and proving rollback under realistic conditions.

### Required deliverables
- [ ] Create a rollout policy defining stages such as pre-production, single-node/site, small tenant cohort, expanded cohort, and full rollout.
- [ ] Define stage entry/exit criteria, observation windows, automatic abort conditions, and maximum exposure/blast radius.
- [ ] Integrate canary selection with tenant/environment/site isolation and configuration revisioning.
- [ ] Automate stage health evaluation using status, telemetry, SLO/error budget, security, and dependency signals.
- [ ] Run and document periodic rollback drills using the same production mechanism.

### Engineering / implementation checklist
- [ ] Define deterministic/controlled cohort selection and prevent accidental simultaneous full-fleet activation.
- [ ] Require candidate artifact/config digest to remain constant across rollout stages unless the rollout is restarted as a new candidate.
- [ ] Include validation/canonical error rates, p95/p99 latency, readiness/degraded state, dependency errors, auth/security anomalies, resource saturation, and audit integrity among gate signals.
- [ ] Define rollback trigger thresholds and whether rollback is automatic or requires operator confirmation by stage.
- [ ] Verify rollback target is a known-good signed artifact/config revision compatible with current state.
- [ ] Test rollback during active traffic, dependency degradation, and partially progressed rollout.
- [ ] Prevent forward rollout when telemetry required for safe decision-making is unavailable unless an explicit emergency policy permits it.
- [ ] Record every stage transition/hold/abort/rollback with actor/automation reason and evidence snapshot.
- [ ] Define emergency-disable path separately from rollback when rollback is unsafe or unavailable.
- [ ] Feed rollout outcome and drill evidence into MC-29 production gate.

### Acceptance / closure criteria
- [ ] No production rollout can jump directly to full scope outside an explicitly authorized emergency procedure.
- [ ] Canary/stage promotion is blocked when required health/security evidence is missing or violates thresholds.
- [ ] A rollback drill demonstrates restoration to a known-good revision within the defined objective and produces machine-readable evidence.
- [ ] Rollout history is auditable by release/configuration digest and cohort.

# Cross-component closure checklist

- [ ] All 40 MC sections have an assigned implementation owner and target milestone.
- [ ] Every Critical component is closed or has an approved, time-bounded exception with compensating controls; production GO must follow the project gate policy.
- [ ] Every changed public contract has a versioned schema/IDL and compatibility tests.
- [ ] Every security control has at least one negative/abuse test and corresponding audit/telemetry evidence.
- [ ] Every operational procedure has been exercised in a drill or test environment using current tooling.
- [ ] Every release artifact and evidence file has an integrity digest; protected artifacts are signed/provenanced according to policy.
- [ ] `REQUIREMENTS_TRACEABILITY.md` is updated so each affected C### control references concrete implementation and verification evidence.
- [ ] `AUDIT_REPORT.md` is regenerated after remediation and does not rely on prose assertions where executable evidence is required.
- [ ] The full CI/certification environment runs with zero unexpected skips and produces a machine-readable final exit-gate artifact.
- [ ] A final post-remediation audit confirms there are no untracked missing components, version mismatches, undocumented dependencies, or stale waivers.

# Recommended remediation waves

1. **Wave A — Production blockers:** MC-02, MC-07, MC-08, MC-10, MC-14, MC-15, MC-16, MC-17, MC-18, MC-29.
2. **Wave B — Contract/configuration foundation:** MC-01, MC-03, MC-04, MC-05, MC-06, MC-09, MC-11, MC-12, MC-13, MC-30.
3. **Wave C — Certification depth:** MC-19, MC-20, MC-21, MC-22, MC-27, MC-28, MC-37, MC-39, MC-40.
4. **Wave D — Operability/governance completion:** MC-23, MC-24, MC-25, MC-26, MC-31, MC-32, MC-33, MC-34, MC-35, MC-36, MC-38.

The wave ordering is a dependency-oriented implementation sequence, not a substitute for the repository's formal severity or production gate.
