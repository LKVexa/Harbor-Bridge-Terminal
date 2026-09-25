# INV-11 Interface Contract Language v4.2.0
## Production Completion — Detailed Engineering Checklists for All Missing Components

**Baseline:** hardened INV-11 v4.2.0 audit, 2026-09-22  
**Scope:** the 40 missing components identified after the v4.2.0 audit  
**Purpose:** convert the gap inventory into implementation-ready, traceable, professional-grade engineering gates.

> The current v4.2.0 package is a hardened reference compatibility model. These checklists describe the additional work required for a production-grade WIT/interface-contract subsystem. Existing v4.2.0 fixes (duplicate function rejection, fail-closed missing-`pk_core` conformance runner, stronger structural validation, complete mixed-diff diagnostics, ordered result diagnostics, dependency-free compatibility core, standalone tests, and release manifest) are treated as baseline capabilities, not open gaps.

## Global completion rules

- `[ ]` means the requirement has not yet been evidenced as complete.
- A component is **complete** only when all mandatory checklist items are satisfied or an approved, scoped, unexpired waiver is linked.
- “PASS” requires objective evidence: automated test result, reviewed design record, generated artifact, benchmark, verification log, or signed acceptance record.
- Missing tools/dependencies, skipped required tests, unavailable reference toolchains, or absent integration environments must be reported as **BLOCKED/NOT RUN**, never converted to PASS.
- Compatibility decisions must be based on structural/semantic rules, not inferred from version strings.
- Inputs should be treated as untrusted unless an explicitly documented deployment profile says otherwise.
- Determinism, bounded resource use, stable reason/diagnostic codes, and reproducible release evidence are cross-cutting release requirements.

## Priority interpretation

- **P0 — Core correctness:** production blocker; implement before claiming complete WIT/interface-contract language support.
- **P1 — Assurance/interoperability:** required before handling hostile or ecosystem-scale inputs in production.
- **P2 — Release/operations:** required for repeatable supportable releases and measurable production behavior.
- **P3 — Lifecycle/operator:** required for mature long-lived governance and safe evolution.

---

# 1. Real WIT lexer/parser and source loader

**Priority:** P0  
**Component ID:** `INV11-MC-01`  
**Objective:** Provide a standards-aligned front end that converts one or more .wit sources into a deterministic, source-spanned internal representation without relying on synthetic Python model construction.

**Primary dependencies:** Component 2 AST/type system; Component 5 diagnostics; Component 15 resource limits.  
**Required deliverables:** Complete WIT grammar/feature-level decision; Streaming or bounded source loader; Token model with spans/trivia policy; Parser API and parse result model; Golden valid/invalid fixture set.

## Component-specific implementation checklist

- [ ] `INV11-MC-01-001` Freeze the exact WIT grammar revision/feature level supported and record unsupported productions explicitly.
- [ ] `INV11-MC-01-002` Define lexical rules for identifiers, keywords, punctuation, comments, whitespace, numeric/version syntax, and escaped text where applicable.
- [ ] `INV11-MC-01-003` Implement byte-to-codepoint handling with explicit UTF-8 validation and deterministic rejection of malformed sequences.
- [ ] `INV11-MC-01-004` Represent every token with file identity, byte offsets, line/column range, token kind, and normalized/raw spelling as required.
- [ ] `INV11-MC-01-005` Preserve enough trivia/comment information to support accurate diagnostics and optional source round-tripping without making compatibility semantics depend on trivia.
- [ ] `INV11-MC-01-006` Implement a source loader for individual files, directories, in-memory buffers, and package entrypoints with canonical path handling.
- [ ] `INV11-MC-01-007` Normalize line endings and source identity without mutating semantic token content.
- [ ] `INV11-MC-01-008` Implement parser productions for packages, worlds, interfaces, use/include/import constructs, type declarations, resources, and functions.
- [ ] `INV11-MC-01-009` Use explicit parser recovery points so one syntax error does not create an uncontrolled cascade of secondary diagnostics.
- [ ] `INV11-MC-01-010` Reject ambiguous or duplicate declarations at the correct grammar/semantic phase with stable diagnostic codes.
- [ ] `INV11-MC-01-011` Return a structured parse result that distinguishes fatal syntax failure, recoverable diagnostics, warnings, and successfully parsed declarations.
- [ ] `INV11-MC-01-012` Ensure parser behavior is deterministic across hash seeds, platforms, file traversal order, and Python optimized mode.
- [ ] `INV11-MC-01-013` Add limits for source bytes, token count, nesting depth, identifier length, declaration count, and diagnostic count.
- [ ] `INV11-MC-01-014` Create golden tests for minimally valid documents, every grammar production, comments/trivia, Unicode identifiers if supported, and boundary syntax.
- [ ] `INV11-MC-01-015` Create negative tests for truncated input, invalid tokens, mismatched delimiters, duplicate modifiers, illegal keyword placement, and malformed versions.
- [ ] `INV11-MC-01-016` Add corpus tests proving multiple source files load in deterministic order and retain independent source spans.
- [ ] `INV11-MC-01-017` Expose a stable parse API that accepts explicit feature/version configuration rather than reading hidden global state.
- [ ] `INV11-MC-01-018` Document parser error-recovery guarantees and cases where parsing intentionally stops.
- [ ] `INV11-MC-01-019` Benchmark tokenization and parse throughput on small, medium, and large WIT corpora.
- [ ] `INV11-MC-01-020` Record parser feature coverage in machine-readable acceptance evidence.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-01-021` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-01-022` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-01-023` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-01-024` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-01-025` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-01-026` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-01-027` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-01-028` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-01-029` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-01-030` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-01-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Real WIT lexer/parser and source loader` as production-ready for its declared scope.

---

# 2. Complete WIT AST/type system

**Priority:** P0  
**Component ID:** `INV11-MC-02`  
**Objective:** Model the complete supported WIT/component interface language with immutable, validated semantic nodes suitable for resolution, normalization, comparison, hashing, and diagnostics.

**Primary dependencies:** Component 1 parser; Component 3 identity; Component 7 recursive graph handling.  
**Required deliverables:** Typed AST/semantic model; Validated constructors/factories; Visitor/traversal API; Type identity/reference model; AST serialization/debug representation.

## Component-specific implementation checklist

- [ ] `INV11-MC-02-001` Define separate syntax AST and resolved semantic model if source fidelity and canonical semantics have different requirements.
- [ ] `INV11-MC-02-002` Model package, world, interface, function, parameter, result, and named type declarations with explicit source ownership.
- [ ] `INV11-MC-02-003` Implement primitive scalar types and every supported aggregate type, including records, tuples, variants, enums, flags, options, results, and lists.
- [ ] `INV11-MC-02-004` Model resources and own/borrow handle semantics explicitly rather than collapsing them to strings.
- [ ] `INV11-MC-02-005` Represent aliases/type references as references that can be resolved without losing the originating declaration path.
- [ ] `INV11-MC-02-006` Define canonical field/case ordering semantics for each type form and prohibit unordered containers where order is observable.
- [ ] `INV11-MC-02-007` Define equality, identity, and equivalence separately so source identity, nominal identity, and structural compatibility are not conflated.
- [ ] `INV11-MC-02-008` Validate duplicate field/case/flag names and invalid empty identifiers at construction or semantic validation time.
- [ ] `INV11-MC-02-009` Validate arity and shape constraints for tuple/result/option/list and any future grammar extensions.
- [ ] `INV11-MC-02-010` Preserve ordered function parameters and ordered/multiple results exactly as represented by the supported WIT level.
- [ ] `INV11-MC-02-011` Attach stable source spans or declaration IDs to all user-authored semantic nodes.
- [ ] `INV11-MC-02-012` Create explicit unresolved-reference node states; never use magic strings or None ambiguously for unresolved symbols.
- [ ] `INV11-MC-02-013` Make nodes immutable after semantic construction or provide a controlled builder phase followed by freeze/validation.
- [ ] `INV11-MC-02-014` Provide deterministic visitor/traversal APIs that work for graph-shaped recursive types without repeated traversal.
- [ ] `INV11-MC-02-015` Add canonical debug/JSON rendering for tests while keeping it distinct from normative machine-readable contract schemas.
- [ ] `INV11-MC-02-016` Add exhaustive unit tests for constructor validation and equality semantics for every node kind.
- [ ] `INV11-MC-02-017` Add round-trip tests from source to AST to normalized semantic model for representative fixtures.
- [ ] `INV11-MC-02-018` Add mutation tests ensuring invalid node states cannot be constructed through public APIs.
- [ ] `INV11-MC-02-019` Document which WIT constructs are intentionally unsupported and the diagnostic emitted for each.
- [ ] `INV11-MC-02-020` Version the semantic model independently enough to support future grammar expansion without breaking stored evidence.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-02-021` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-02-022` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-02-023` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-02-024` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-02-025` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-02-026` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-02-027` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-02-028` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-02-029` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-02-030` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-02-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Complete WIT AST/type system` as production-ready for its declared scope.

---

# 3. Package/world identity model

**Priority:** P0  
**Component ID:** `INV11-MC-03`  
**Objective:** Define stable nominal identity for packages, versions, worlds, interfaces, and declarations so references and compatibility comparisons cannot collide or drift.

**Primary dependencies:** Component 2 AST/type system; Component 4 resolver; Component 6 normalization.  
**Required deliverables:** Qualified identifier grammar; Identity value objects; Version/range policy; Canonical string form; Identity collision tests.

## Component-specific implementation checklist

- [ ] `INV11-MC-03-001` Specify namespace, package name, semantic version, world, interface, and declaration identity components precisely.
- [ ] `INV11-MC-03-002` Define canonical fully qualified identifier syntax and escaping rules.
- [ ] `INV11-MC-03-003` Use structured identity objects internally rather than concatenated ad-hoc strings.
- [ ] `INV11-MC-03-004` Define whether package versions are exact, ranged, optional, or selected by resolver policy and keep those semantics explicit.
- [ ] `INV11-MC-03-005` Separate source-location identity from nominal language identity.
- [ ] `INV11-MC-03-006` Define identity for anonymous/inline types using stable enclosing declaration paths or canonical structural IDs as appropriate.
- [ ] `INV11-MC-03-007` Define identity behavior across aliases, re-exports, use/import statements, and included worlds/interfaces.
- [ ] `INV11-MC-03-008` Reject malformed namespaces, empty segments, invalid version syntax, and duplicate world/interface declarations.
- [ ] `INV11-MC-03-009` Specify case sensitivity and Unicode normalization policy for all identity segments.
- [ ] `INV11-MC-03-010` Ensure identity hashing is deterministic and not based on Python process hash randomization.
- [ ] `INV11-MC-03-011` Define comparison rules for same logical package at different versions without inferring compatibility from the version string.
- [ ] `INV11-MC-03-012` Add collision tests for identical short names in different namespaces/packages/worlds/interfaces.
- [ ] `INV11-MC-03-013` Add tests for multiple versions of the same package in one dependency graph.
- [ ] `INV11-MC-03-014` Provide parse/render round-trip tests for every qualified identifier form.
- [ ] `INV11-MC-03-015` Expose identity in diagnostics, telemetry, diff paths, and evidence bundles using one canonical renderer.
- [ ] `INV11-MC-03-016` Document rules for renames/moves and whether they are breaking, aliasable, or unsupported.
- [ ] `INV11-MC-03-017` Add schema constraints for identity values in machine-readable contracts.
- [ ] `INV11-MC-03-018` Ensure canonical identity remains stable under file reordering and non-semantic source formatting changes.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-03-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-03-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-03-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-03-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-03-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-03-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-03-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-03-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-03-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-03-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-03-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Package/world identity model` as production-ready for its declared scope.

---

# 4. Import/include/use dependency resolver

**Priority:** P0  
**Component ID:** `INV11-MC-04`  
**Objective:** Resolve all inter-package and intra-package references deterministically, detect cycles/conflicts, and produce a complete resolved dependency graph with auditable selection decisions.

**Primary dependencies:** Components 1–3; Component 5 diagnostics; Component 18 version matrix.  
**Required deliverables:** Resolver engine; Dependency graph model; Version-selection policy; Cycle/conflict diagnostics; Resolution lock/evidence output.

## Component-specific implementation checklist

- [ ] `INV11-MC-04-001` Enumerate all dependency-bearing language constructs and define the exact resolution phase for each.
- [ ] `INV11-MC-04-002` Resolve local declarations before external packages using a documented precedence model.
- [ ] `INV11-MC-04-003` Canonicalize dependency keys using the package/world identity model.
- [ ] `INV11-MC-04-004` Implement deterministic graph construction independent of filesystem enumeration order.
- [ ] `INV11-MC-04-005` Detect direct and indirect cycles and emit the complete minimal cycle path in diagnostics.
- [ ] `INV11-MC-04-006` Define version selection rules, including exact-match behavior, ranges if supported, duplicate versions, and conflict refusal.
- [ ] `INV11-MC-04-007` Refuse ambiguous multi-provider resolutions unless an explicit policy deterministically selects one.
- [ ] `INV11-MC-04-008` Resolve use/import aliases without losing the underlying canonical identity.
- [ ] `INV11-MC-04-009` Track provenance of every resolved edge: source declaration, selected target, version, source repository/path, and digest when available.
- [ ] `INV11-MC-04-010` Implement topological ordering for acyclic dependency phases and graph-safe processing for allowed recursion.
- [ ] `INV11-MC-04-011` Support bounded resolution depth and dependency fan-out to prevent adversarial graph amplification.
- [ ] `INV11-MC-04-012` Provide a lock/evidence representation capturing the selected dependency graph for reproducibility.
- [ ] `INV11-MC-04-013` Invalidate caches when source digest, resolver policy, feature level, or dependency version changes.
- [ ] `INV11-MC-04-014` Add unit tests for local imports, external imports, includes, aliases, transitive dependencies, and re-exports.
- [ ] `INV11-MC-04-015` Add negative tests for missing targets, duplicate targets, incompatible versions, cycles, shadowing, and ambiguous aliases.
- [ ] `INV11-MC-04-016` Add deterministic-resolution tests that randomize file and dependency discovery order.
- [ ] `INV11-MC-04-017` Integrate resolver failures with stable diagnostic codes and related source spans.
- [ ] `INV11-MC-04-018` Document offline/disconnected resolution behavior and registry/cache trust assumptions.
- [ ] `INV11-MC-04-019` Emit resolution metrics: nodes, edges, depth, conflicts, cache hits, and elapsed time.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-04-020` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-04-021` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-04-022` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-04-023` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-04-024` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-04-025` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-04-026` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-04-027` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-04-028` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-04-029` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-04-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Import/include/use dependency resolver` as production-ready for its declared scope.

---

# 5. Source-span-aware diagnostics

**Priority:** P0  
**Component ID:** `INV11-MC-05`  
**Objective:** Create a stable diagnostic subsystem that reports actionable parse, resolution, validation, compatibility, and policy failures with precise source attribution.

**Primary dependencies:** Components 1–4; Component 37 human-readable diff renderer.  
**Required deliverables:** Diagnostic data model; Stable code registry; Renderer(s); Related-location support; Machine-readable diagnostic schema.

## Component-specific implementation checklist

- [ ] `INV11-MC-05-001` Define severity levels with normative meanings: error, warning, info/note, and internal failure.
- [ ] `INV11-MC-05-002` Allocate stable diagnostic code namespaces by subsystem and prohibit reuse with changed meaning.
- [ ] `INV11-MC-05-003` Represent primary file/span, zero or more related spans, symbol path, package identity, and remediation hints.
- [ ] `INV11-MC-05-004` Support diagnostics not tied to source text, such as provenance or release-policy failures, without fake line numbers.
- [ ] `INV11-MC-05-005` Define byte-offset versus character-column semantics and handle Unicode consistently.
- [ ] `INV11-MC-05-006` Render concise single-line diagnostics and expanded compiler-style diagnostics from the same structured object.
- [ ] `INV11-MC-05-007` Provide machine-readable JSON serialization with schema version and deterministic field ordering.
- [ ] `INV11-MC-05-008` Cap diagnostic count and cascade depth under malformed input.
- [ ] `INV11-MC-05-009` Deduplicate semantically identical diagnostics while preserving distinct source locations.
- [ ] `INV11-MC-05-010` Avoid embedding nondeterministic absolute temporary paths in canonical evidence output.
- [ ] `INV11-MC-05-011` Include offending and related symbol identities where available.
- [ ] `INV11-MC-05-012` Define redaction policy for file paths or source excerpts in security-sensitive environments.
- [ ] `INV11-MC-05-013` Add golden rendering tests for parse, resolution, duplicate symbol, incompatible type, version conflict, and limit-exceeded cases.
- [ ] `INV11-MC-05-014` Add tests for tabs, Unicode, CRLF/LF, multibyte characters, and end-of-file spans.
- [ ] `INV11-MC-05-015` Validate that each public failure mode maps to a documented diagnostic code.
- [ ] `INV11-MC-05-016` Add a code registry lint that fails CI on duplicate or undocumented diagnostic IDs.
- [ ] `INV11-MC-05-017` Document diagnostic stability guarantees across minor/major releases.
- [ ] `INV11-MC-05-018` Expose diagnostics directly in acceptance evidence bundles and CLI exit behavior.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-05-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-05-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-05-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-05-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-05-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-05-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-05-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-05-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-05-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-05-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-05-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Source-span-aware diagnostics` as production-ready for its declared scope.

---

# 6. Canonical structural normalization

**Priority:** P0  
**Component ID:** `INV11-MC-06`  
**Objective:** Convert resolved interfaces into a deterministic, semantics-preserving canonical form before comparison, caching, hashing, signing, or evidence emission.

**Primary dependencies:** Components 2–4; Component 7 recursive graphs; Component 16 fingerprints.  
**Required deliverables:** Canonical model; Normalization algorithm; Canonical serializer; Idempotence tests; Normalization version identifier.

## Component-specific implementation checklist

- [ ] `INV11-MC-06-001` Define precisely which source distinctions are semantic and which are discarded during normalization.
- [ ] `INV11-MC-06-002` Assign a normalization-format version and include it in every canonical artifact/fingerprint input.
- [ ] `INV11-MC-06-003` Canonicalize qualified identities using the identity model and resolved dependency selection.
- [ ] `INV11-MC-06-004` Preserve semantically ordered constructs such as parameters, results, tuple fields, and any ordered cases.
- [ ] `INV11-MC-06-005` Sort only constructs whose language semantics are explicitly order-insensitive, using stable keys.
- [ ] `INV11-MC-06-006` Resolve aliases according to a documented rule while retaining nominal boundaries when compatibility semantics require them.
- [ ] `INV11-MC-06-007` Normalize equivalent primitive/type spellings only where the language specification defines equivalence.
- [ ] `INV11-MC-06-008` Represent recursive references using stable graph IDs rather than traversal-order-dependent object IDs.
- [ ] `INV11-MC-06-009` Exclude source spans, comments, local file paths, timestamps, and process-specific values from semantic canonical bytes.
- [ ] `INV11-MC-06-010` Use an unambiguous length-delimited or schema-defined serialization rather than string concatenation.
- [ ] `INV11-MC-06-011` Prove normalization is idempotent: N(N(x)) == N(x).
- [ ] `INV11-MC-06-012` Prove semantically irrelevant source reordering/formatting yields identical canonical output.
- [ ] `INV11-MC-06-013` Prove semantically meaningful order changes remain observable where required.
- [ ] `INV11-MC-06-014` Add golden canonical outputs for representative interfaces/worlds/packages.
- [ ] `INV11-MC-06-015` Add compatibility tests across normalization-version boundaries and refuse silent cross-version hash comparison.
- [ ] `INV11-MC-06-016` Benchmark normalization CPU/memory on large graphs.
- [ ] `INV11-MC-06-017` Document any intentionally lossy normalization and why it cannot affect compatibility decisions.
- [ ] `INV11-MC-06-018` Expose canonical-form inspection for debugging without encouraging callers to depend on internal field layout.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-06-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-06-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-06-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-06-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-06-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-06-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-06-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-06-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-06-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-06-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-06-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Canonical structural normalization` as production-ready for its declared scope.

---

# 7. Recursive type graph handling

**Priority:** P0  
**Component ID:** `INV11-MC-07`  
**Objective:** Support recursive and mutually recursive type definitions safely and deterministically in resolution, normalization, hashing, diffing, and compatibility classification.

**Primary dependencies:** Components 2,4,6; Component 8 compatibility rules; Component 15 resource limits.  
**Required deliverables:** Graph model/cycle guards; Stable node numbering; Recursive equality/comparison engine; Cycle diagnostics; Stress fixtures.

## Component-specific implementation checklist

- [ ] `INV11-MC-07-001` Represent resolved type relations as graph edges rather than assuming an acyclic tree.
- [ ] `INV11-MC-07-002` Distinguish legal type recursion from illegal dependency/import cycles according to the language rules.
- [ ] `INV11-MC-07-003` Use visited-pair memoization for structural comparison to prevent infinite recursion.
- [ ] `INV11-MC-07-004` Use deterministic node identity independent of object memory addresses.
- [ ] `INV11-MC-07-005` Define strongly connected component handling for mutually recursive type groups.
- [ ] `INV11-MC-07-006` Ensure hashing/fingerprinting uses a graph-canonical algorithm or stable fixpoint/SCC representation.
- [ ] `INV11-MC-07-007` Define compatibility semantics when recursion shape changes but reachable structure remains equivalent.
- [ ] `INV11-MC-07-008` Detect graph expansion attacks and enforce node/edge/recursion work budgets.
- [ ] `INV11-MC-07-009` Guarantee stack safety using iterative traversal or bounded recursion for adversarially deep graphs.
- [ ] `INV11-MC-07-010` Cache comparison results for repeated subgraphs with keys that include policy/normalization versions.
- [ ] `INV11-MC-07-011` Emit useful cycle paths in diagnostics without printing unbounded recursive structures.
- [ ] `INV11-MC-07-012` Create fixtures for self-recursive records/resources and mutually recursive multi-type groups.
- [ ] `INV11-MC-07-013` Create negative fixtures for illegal cycles, unresolved back edges, and cycle-through-version-conflict cases.
- [ ] `INV11-MC-07-014` Add randomized traversal-order tests to prove deterministic classification/reasons.
- [ ] `INV11-MC-07-015` Add large SCC stress tests and memory profiling.
- [ ] `INV11-MC-07-016` Verify canonical serialization and fingerprint stability for equivalent recursive graphs.
- [ ] `INV11-MC-07-017` Document worst-case complexity and explicit safety limits.
- [ ] `INV11-MC-07-018` Add regression tests for every discovered recursion-related bug.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-07-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-07-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-07-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-07-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-07-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-07-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-07-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-07-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-07-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-07-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-07-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Recursive type graph handling` as production-ready for its declared scope.

---

# 8. Complete structural compatibility rules

**Priority:** P0  
**Component ID:** `INV11-MC-08`  
**Objective:** Implement explicit, testable compatibility semantics for every supported WIT construct and evolution direction rather than only function-name/signature subsets.

**Primary dependencies:** Components 2,6,7; Component 10 policy corpus; Component 33 semver recommendations.  
**Required deliverables:** Compatibility policy specification; Rule engine; Directional diff classification; Reason-code taxonomy; Rule coverage matrix.

## Component-specific implementation checklist

- [ ] `INV11-MC-08-001` Define compatibility direction explicitly: old producer/new consumer, old consumer/new producer, or bidirectional mode.
- [ ] `INV11-MC-08-002` Define top-level classifications and whether additive, compatible, breaking, unknown, or policy-blocked states are distinct.
- [ ] `INV11-MC-08-003` Specify rules for function addition, removal, rename, parameter addition/removal/reorder/type change, and result changes.
- [ ] `INV11-MC-08-004` Specify record field addition/removal/reorder/rename/type changes and whether field order is semantically relevant.
- [ ] `INV11-MC-08-005` Specify variant case evolution, payload evolution, and exhaustiveness implications.
- [ ] `INV11-MC-08-006` Specify enum and flags member additions/removals/renames with consumer/producer directionality.
- [ ] `INV11-MC-08-007` Specify option/result/list/tuple nested evolution recursively.
- [ ] `INV11-MC-08-008` Specify resource method/constructor/static function evolution and own/borrow handle compatibility.
- [ ] `INV11-MC-08-009` Specify alias changes, nominal versus structural type equivalence, and moves across interfaces/packages.
- [ ] `INV11-MC-08-010` Specify world import/export additions/removals and interface reference changes.
- [ ] `INV11-MC-08-011` Define behavior for unknown future node kinds: fail closed or explicit unknown, never implicit compatible.
- [ ] `INV11-MC-08-012` Use stable machine-readable reason codes separate from human prose.
- [ ] `INV11-MC-08-013` Collect all relevant diff reasons without suppressing additive information when a breaking change exists.
- [ ] `INV11-MC-08-014` Guarantee deterministic reason ordering using canonical declaration paths.
- [ ] `INV11-MC-08-015` Implement policy versioning so historical release evidence can reproduce the exact classification rules used.
- [ ] `INV11-MC-08-016` Create one positive and one negative minimum fixture per rule, plus nested/composed cases.
- [ ] `INV11-MC-08-017` Add metamorphic tests such as identity compatibility and symmetry only where semantically valid.
- [ ] `INV11-MC-08-018` Cross-check compatibility results against adapter generation eligibility so unsafe shims are never proposed.
- [ ] `INV11-MC-08-019` Document intentional deviations from official component-model/WIT compatibility expectations.
- [ ] `INV11-MC-08-020` Require architecture approval for any change that reclassifies an existing fixture.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-08-021` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-08-022` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-08-023` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-08-024` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-08-025` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-08-026` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-08-027` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-08-028` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-08-029` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-08-030` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-08-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Complete structural compatibility rules` as production-ready for its declared scope.

---

# 9. Schema-defined machine-readable contracts

**Priority:** P0  
**Component ID:** `INV11-MC-09`  
**Objective:** Formalize PK_INTERFACE/1 and PK_INTERFACE_DIFF/1 as versioned schemas with validation, evolution, deterministic serialization, and clear compatibility guarantees.

**Primary dependencies:** Components 3,5,6,8; Component 38 evidence bundle.  
**Required deliverables:** JSON Schema or equivalent; Normative examples; Schema validators; Evolution policy; Schema conformance tests.

## Component-specific implementation checklist

- [ ] `INV11-MC-09-001` Document the normative purpose and trust boundary of PK_INTERFACE/1 and PK_INTERFACE_DIFF/1.
- [ ] `INV11-MC-09-002` Choose a schema technology and pin its draft/version in repository metadata.
- [ ] `INV11-MC-09-003` Define required versus optional fields, nullability, enums, patterns, maximum sizes, and additionalProperties policy.
- [ ] `INV11-MC-09-004` Represent package/world/interface identity with structured schema fields rather than ambiguous free-form names.
- [ ] `INV11-MC-09-005` Include schema format version, normalization version, compatibility-policy version, and tool version.
- [ ] `INV11-MC-09-006` Represent diagnostics/reasons with stable codes and structured symbol paths.
- [ ] `INV11-MC-09-007` Define canonical serialization requirements for signing/fingerprinting if schema documents are signed.
- [ ] `INV11-MC-09-008` Specify forward/backward schema evolution rules and consumer behavior on unknown fields.
- [ ] `INV11-MC-09-009` Define how large source excerpts or sensitive local paths are excluded/redacted.
- [ ] `INV11-MC-09-010` Generate or maintain validators used both in tests and runtime ingestion boundaries.
- [ ] `INV11-MC-09-011` Reject duplicate keys, invalid Unicode, oversized values, and non-conforming numeric forms at ingestion.
- [ ] `INV11-MC-09-012` Create positive schema fixtures covering minimal and maximal representative documents.
- [ ] `INV11-MC-09-013` Create negative fixtures for every required-field/type/enum/pattern constraint.
- [ ] `INV11-MC-09-014` Add round-trip encode/decode tests preserving normative meaning.
- [ ] `INV11-MC-09-015` Add compatibility tests proving old readers handle allowed new-schema documents as promised.
- [ ] `INV11-MC-09-016` Publish human-readable schema documentation generated from the normative definition where practical.
- [ ] `INV11-MC-09-017` Include schema digests in release evidence.
- [ ] `INV11-MC-09-018` Treat schema validation failure as a distinct diagnostic and gate failure.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-09-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-09-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-09-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-09-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-09-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-09-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-09-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-09-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-09-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-09-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-09-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Schema-defined machine-readable contracts` as production-ready for its declared scope.

---

# 10. Compatibility-policy test corpus

**Priority:** P0  
**Component ID:** `INV11-MC-10`  
**Objective:** Build a normative, reviewable fixture corpus that proves every compatibility rule and boundary case and prevents silent policy drift.

**Primary dependencies:** Components 1–9; Component 11 differential testing.  
**Required deliverables:** Fixture taxonomy; Expected-result manifest; Golden reason outputs; Corpus runner; Coverage report.

## Component-specific implementation checklist

- [ ] `INV11-MC-10-001` Create a machine-readable fixture manifest mapping each case to rule IDs, expected class, and expected reason codes.
- [ ] `INV11-MC-10-002` Include exact no-change and source-format-only change controls.
- [ ] `INV11-MC-10-003` Include every top-level WIT construct and every supported nested type form.
- [ ] `INV11-MC-10-004` Create producer-to-consumer and consumer-to-producer directional cases where results differ.
- [ ] `INV11-MC-10-005` Create additive, breaking, compatible, invalid, unresolved, and limit-exceeded examples.
- [ ] `INV11-MC-10-006` Cover rename versus remove+add semantics explicitly.
- [ ] `INV11-MC-10-007` Cover parameter/result ordering changes and duplicate/invalid declarations.
- [ ] `INV11-MC-10-008` Cover resource ownership/borrowing and lifecycle method changes.
- [ ] `INV11-MC-10-009` Cover world imports/exports and transitive dependency version changes.
- [ ] `INV11-MC-10-010` Cover recursive and mutually recursive types.
- [ ] `INV11-MC-10-011` Include minimal one-change fixtures to isolate each rule and complex fixtures combining multiple changes.
- [ ] `INV11-MC-10-012` Store expected structured reason codes and canonical declaration paths, not only prose snapshots.
- [ ] `INV11-MC-10-013` Require deterministic output across repeated runs and shuffled source discovery order.
- [ ] `INV11-MC-10-014` Run corpus against normal and optimized Python modes.
- [ ] `INV11-MC-10-015` Tag regression fixtures with issue/finding identifiers and never delete them without architecture review.
- [ ] `INV11-MC-10-016` Measure rule coverage and fail CI when a compatibility rule has no fixture.
- [ ] `INV11-MC-10-017` Version the corpus alongside the compatibility-policy version.
- [ ] `INV11-MC-10-018` Publish a concise policy matrix generated from the same fixture metadata.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-10-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-10-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-10-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-10-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-10-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-10-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-10-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-10-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-10-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-10-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-10-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Compatibility-policy test corpus` as production-ready for its declared scope.

---

# 11. Official-tool differential testing

**Priority:** P1  
**Component ID:** `INV11-MC-11`  
**Objective:** Continuously compare INV-11 parsing, resolution, and normalization behavior with a pinned authoritative WIT/WebAssembly component toolchain and triage intentional versus accidental divergence.

**Primary dependencies:** Components 1–10; Component 18 version matrix.  
**Required deliverables:** Reference-tool adapter; Pinned toolchain manifest; Differential runner; Divergence allowlist; Reproduction bundles.

## Component-specific implementation checklist

- [ ] `INV11-MC-11-001` Select and document the authoritative reference tool(s) and exact versions used for each supported WIT feature level.
- [ ] `INV11-MC-11-002` Define comparable outputs: accepted/rejected source, parsed structure, resolved identities, canonical form, or diagnostic class.
- [ ] `INV11-MC-11-003` Build an adapter that invokes the reference tool in a hermetic, timeout-bounded subprocess or container.
- [ ] `INV11-MC-11-004` Normalize non-semantic diagnostic wording before comparison while preserving acceptance and semantic structure.
- [ ] `INV11-MC-11-005` Create differential cases from the WIT fixture corpus and compatibility-policy corpus.
- [ ] `INV11-MC-11-006` Run both tools on identical bytes and dependency graphs.
- [ ] `INV11-MC-11-007` Classify divergences as INV-11 defect, reference-tool defect/limitation, version mismatch, or intentional policy difference.
- [ ] `INV11-MC-11-008` Require an explicit reviewed allowlist entry with expiry for intentional divergences.
- [ ] `INV11-MC-11-009` Capture tool versions, command line, environment, input digest, stdout/stderr digests, and exit codes in reproduction evidence.
- [ ] `INV11-MC-11-010` Fail CI on new unreviewed divergences.
- [ ] `INV11-MC-11-011` Add timeout, crash, malformed-output, and missing-reference-tool handling that cannot produce false green results.
- [ ] `INV11-MC-11-012` Test cross-platform consistency where the authoritative tool is supported.
- [ ] `INV11-MC-11-013` Run a small smoke set per change and a larger scheduled corpus in release qualification.
- [ ] `INV11-MC-11-014` Track divergence count and age as release metrics.
- [ ] `INV11-MC-11-015` Document how reference-tool changes trigger compatibility reassessment rather than automatic acceptance.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-11-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-11-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-11-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-11-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-11-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-11-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-11-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-11-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-11-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-11-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-11-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Official-tool differential testing` as production-ready for its declared scope.

---

# 12. WIT fixture corpus

**Priority:** P1  
**Component ID:** `INV11-MC-12`  
**Objective:** Maintain a broad, legally usable corpus of real-world and synthetic WIT packages that exercises representative grammar, dependency, versioning, and resource patterns.

**Primary dependencies:** Components 1–4; Component 11 differential testing.  
**Required deliverables:** Curated corpus; License/provenance metadata; Corpus index; Expected parse metadata; Corpus update process.

## Component-specific implementation checklist

- [ ] `INV11-MC-12-001` Define corpus categories by grammar feature, package complexity, dependency depth, resources, and versioning behavior.
- [ ] `INV11-MC-12-002` Include small synthetic fixtures for isolation and larger real-world fixtures for realism.
- [ ] `INV11-MC-12-003` Record origin, license, source URL/reference, revision, and local modifications for every third-party fixture.
- [ ] `INV11-MC-12-004` Avoid fixtures with unclear redistribution rights.
- [ ] `INV11-MC-12-005` Store source bytes deterministically and preserve original line endings only when relevant to a test.
- [ ] `INV11-MC-12-006` Include multi-file packages, multiple worlds, imports/includes/use, nested dependencies, aliases, resources, and recursive types.
- [ ] `INV11-MC-12-007` Include multiple versions of selected packages to test identity and resolver behavior.
- [ ] `INV11-MC-12-008` Include intentionally invalid fixtures in a separate negative corpus with expected diagnostic codes.
- [ ] `INV11-MC-12-009` Assign stable fixture IDs so historical test evidence remains traceable across file moves.
- [ ] `INV11-MC-12-010` Record expected feature level and minimum/maximum reference-tool versions.
- [ ] `INV11-MC-12-011` Generate a corpus inventory with file count, bytes, tokens, declarations, graph depth, and node count.
- [ ] `INV11-MC-12-012` Add integrity digests so accidental corpus mutation is detected.
- [ ] `INV11-MC-12-013` Create a review process for corpus additions/removals and license changes.
- [ ] `INV11-MC-12-014` Run parse/normalize determinism checks over the complete corpus during release qualification.
- [ ] `INV11-MC-12-015` Use corpus partitions for smoke, standard CI, extended CI, and soak testing.
- [ ] `INV11-MC-12-016` Document how to reproduce each corpus case independently.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-12-017` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-12-018` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-12-019` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-12-020` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-12-021` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-12-022` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-12-023` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-12-024` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-12-025` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-12-026` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-12-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `WIT fixture corpus` as production-ready for its declared scope.

---

# 13. Property-based and mutation testing

**Priority:** P1  
**Component ID:** `INV11-MC-13`  
**Objective:** Use generated valid/invalid semantic structures and controlled mutations to prove invariants that example-based tests can miss.

**Primary dependencies:** Components 2,7,8,10.  
**Required deliverables:** Generators/strategies; Invariant catalog; Mutation operators; Shrinking/repro seeds; CI profiles.

## Component-specific implementation checklist

- [ ] `INV11-MC-13-001` Define generators for identifiers, primitives, nested types, functions, interfaces, worlds, packages, and dependency graphs.
- [ ] `INV11-MC-13-002` Generate only spec-valid structures for semantic invariants and separately generate targeted invalid structures for validation tests.
- [ ] `INV11-MC-13-003` Bound depth, width, and graph cycles so generation remains productive and reproducible.
- [ ] `INV11-MC-13-004` Define invariants such as classify(x,x)=compatible/no-change according to policy semantics.
- [ ] `INV11-MC-13-005` Define normalization idempotence and fingerprint stability invariants.
- [ ] `INV11-MC-13-006` Define parse/render or model serialization round-trip invariants where the format promises them.
- [ ] `INV11-MC-13-007` Define resolver invariants under randomized file discovery order.
- [ ] `INV11-MC-13-008` Implement mutation operators for add/remove/rename/reorder/change-type/change-version/change-ownership operations.
- [ ] `INV11-MC-13-009` Check that mutations expected to be breaking/additive produce the documented class and reason code.
- [ ] `INV11-MC-13-010` Use shrinking to minimize failing graphs into actionable regression cases.
- [ ] `INV11-MC-13-011` Persist failing seeds and minimized artifacts in a regression directory.
- [ ] `INV11-MC-13-012` Set deterministic CI seeds while also running rotating/random seeds in scheduled jobs.
- [ ] `INV11-MC-13-013` Track generated case counts, discard rates, and rule coverage.
- [ ] `INV11-MC-13-014` Guard against property tests silently skipping due to missing optional dependencies.
- [ ] `INV11-MC-13-015` Run property tests under normal and optimized modes.
- [ ] `INV11-MC-13-016` Document any invariants that are directional rather than symmetric.
- [ ] `INV11-MC-13-017` Promote every discovered defect into a fixed regression fixture.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-13-018` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-13-019` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-13-020` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-13-021` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-13-022` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-13-023` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-13-024` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-13-025` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-13-026` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-13-027` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-13-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Property-based and mutation testing` as production-ready for its declared scope.

---

# 14. Parser/schema fuzzing

**Priority:** P1  
**Component ID:** `INV11-MC-14`  
**Objective:** Continuously fuzz source and machine-readable inputs to find crashes, hangs, parser differentials, excessive resource consumption, and validation bypasses.

**Primary dependencies:** Components 1,9,15; Component 23 CI.  
**Required deliverables:** Fuzz targets; Seed corpus; Dictionary/token hints; Crash triage pipeline; Reproducer retention.

## Component-specific implementation checklist

- [ ] `INV11-MC-14-001` Create separate fuzz targets for lexer/parser, source loader, schema decoder, canonicalizer, and compatibility-diff ingestion.
- [ ] `INV11-MC-14-002` Seed fuzzers with minimal valid documents and representative corpus samples.
- [ ] `INV11-MC-14-003` Add grammar/token dictionaries to improve mutation reach without over-constraining discovery.
- [ ] `INV11-MC-14-004` Exercise malformed UTF-8, truncated multibyte sequences, invalid escapes, very long identifiers, and embedded NULs.
- [ ] `INV11-MC-14-005` Exercise extreme nesting, huge lists, repeated declarations, cyclic references, and alias chains.
- [ ] `INV11-MC-14-006` Exercise JSON/schema hazards including duplicate keys, deep arrays/objects, oversized strings, and unknown enums.
- [ ] `INV11-MC-14-007` Treat crash, assertion failure, uncaught exception, timeout, excessive allocation, and inconsistent classification as findings.
- [ ] `INV11-MC-14-008` Run fuzz targets with strict CPU, memory, input-size, and wall-clock limits.
- [ ] `INV11-MC-14-009` Make fuzz entrypoints deterministic for a given input and configuration.
- [ ] `INV11-MC-14-010` Minimize crashing inputs automatically and retain exact tool/version metadata.
- [ ] `INV11-MC-14-011` Deduplicate findings by stack/signature plus semantic failure class.
- [ ] `INV11-MC-14-012` Convert fixed fuzz findings into permanent regression tests.
- [ ] `INV11-MC-14-013` Run short fuzz-smoke in CI and longer campaigns in scheduled/release jobs.
- [ ] `INV11-MC-14-014` Instrument coverage where supported and track meaningful parser/validator reach.
- [ ] `INV11-MC-14-015` Document responsible handling for potential security-impacting parser defects.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-14-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-14-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-14-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-14-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-14-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-14-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-14-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-14-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-14-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-14-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-14-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Parser/schema fuzzing` as production-ready for its declared scope.

---

# 15. Resource-exhaustion controls

**Priority:** P1  
**Component ID:** `INV11-MC-15`  
**Objective:** Protect parsing, resolution, normalization, comparison, and rendering from CPU, memory, stack, graph, and output-amplification attacks.

**Primary dependencies:** Components 1,4,7,14; Component 28 capacity model.  
**Required deliverables:** Central limit configuration; Budget accounting; Limit diagnostics; Adversarial tests; Operational defaults.

## Component-specific implementation checklist

- [ ] `INV11-MC-15-001` Define hard and configurable limits for source bytes per file and aggregate package bytes.
- [ ] `INV11-MC-15-002` Define token, declaration, symbol, interface, function, field/case, and dependency counts.
- [ ] `INV11-MC-15-003` Define maximum lexical identifier/string length and maximum diagnostic excerpt length.
- [ ] `INV11-MC-15-004` Define syntax nesting, semantic type nesting, dependency depth, and graph node/edge limits.
- [ ] `INV11-MC-15-005` Define comparison work budget, visited-pair count, and maximum diff reason count.
- [ ] `INV11-MC-15-006` Define maximum canonical serialization/evidence output size.
- [ ] `INV11-MC-15-007` Use checked arithmetic for counters/size accumulation and reject overflow conditions.
- [ ] `INV11-MC-15-008` Centralize limits in an immutable policy object passed explicitly through public entrypoints.
- [ ] `INV11-MC-15-009` Emit stable limit-exceeded diagnostics naming the consumed resource and configured limit without exposing sensitive internals.
- [ ] `INV11-MC-15-010` Fail before allocating proportional memory when declared/input size already exceeds a limit.
- [ ] `INV11-MC-15-011` Use iterative traversal where feasible to avoid interpreter stack exhaustion.
- [ ] `INV11-MC-15-012` Add adversarial tests just below, at, and above every limit.
- [ ] `INV11-MC-15-013` Add compound tests that combine moderate values across multiple dimensions to expose multiplicative blowups.
- [ ] `INV11-MC-15-014` Benchmark overhead of budget accounting and ensure it does not dominate normal workloads.
- [ ] `INV11-MC-15-015` Document trusted/offline profiles if operators may raise limits, including associated risk.
- [ ] `INV11-MC-15-016` Include active limits in telemetry and acceptance evidence for reproducibility.
- [ ] `INV11-MC-15-017` Never auto-relax limits based on input claims or version strings.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-15-018` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-15-019` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-15-020` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-15-021` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-15-022` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-15-023` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-15-024` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-15-025` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-15-026` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-15-027` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-15-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Resource-exhaustion controls` as production-ready for its declared scope.

---

# 16. Deterministic hashing/fingerprints

**Priority:** P1  
**Component ID:** `INV11-MC-16`  
**Objective:** Produce stable cryptographic fingerprints for normalized interfaces, packages, dependency graphs, and evidence inputs suitable for provenance and cache keys.

**Primary dependencies:** Components 3,6,7; Component 17 provenance; Component 30 audit events.  
**Required deliverables:** Fingerprint spec; Hash implementation; Domain separators; Test vectors; Migration policy.

## Component-specific implementation checklist

- [ ] `INV11-MC-16-001` Select approved cryptographic hash algorithm(s) and document security/longevity assumptions.
- [ ] `INV11-MC-16-002` Hash canonical bytes only; never hash mutable Python repr() or process-dependent structures.
- [ ] `INV11-MC-16-003` Include explicit domain separation for interface, package, dependency graph, diff, and evidence fingerprints.
- [ ] `INV11-MC-16-004` Include normalization/policy/schema version where needed to prevent cross-version semantic collisions.
- [ ] `INV11-MC-16-005` Define whether external dependency digests are included transitively and how graph ordering is canonicalized.
- [ ] `INV11-MC-16-006` Avoid incorporating timestamps, absolute paths, random IDs, or environment-specific data.
- [ ] `INV11-MC-16-007` Use length-delimited structured encoding to prevent concatenation ambiguity.
- [ ] `INV11-MC-16-008` Expose fingerprints using a self-describing algorithm prefix or structured field.
- [ ] `INV11-MC-16-009` Generate fixed test vectors and validate across supported platforms/interpreters.
- [ ] `INV11-MC-16-010` Test equivalent source formatting and discovery-order changes yield the same semantic fingerprint.
- [ ] `INV11-MC-16-011` Test any semantic change expected to affect compatibility produces a different relevant fingerprint.
- [ ] `INV11-MC-16-012` Define collision/error handling and never use truncated fingerprints below an approved strength for security decisions.
- [ ] `INV11-MC-16-013` Define fingerprint migration behavior if the algorithm or canonical format changes.
- [ ] `INV11-MC-16-014` Use fingerprints consistently in caches, provenance, audit events, and evidence bundles.
- [ ] `INV11-MC-16-015` Document that fingerprints prove byte/canonical identity, not authenticity by themselves.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-16-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-16-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-16-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-16-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-16-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-16-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-16-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-16-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-16-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-16-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-16-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Deterministic hashing/fingerprints` as production-ready for its declared scope.

---

# 17. Signed artifact/provenance verification hook

**Priority:** P1  
**Component ID:** `INV11-MC-17`  
**Objective:** Verify imported contract packages against digest, signature, SBOM, and provenance policy before they influence resolution or compatibility decisions.

**Primary dependencies:** Component 16 fingerprints; Component 31 signing/SBOM; Component 4 resolver.  
**Required deliverables:** Verification provider API; Trust policy model; Signature/provenance adapters; Verification diagnostics; Test fixtures.

## Component-specific implementation checklist

- [ ] `INV11-MC-17-001` Define a provider-neutral verification interface so signature technology can change without coupling core semantics.
- [ ] `INV11-MC-17-002` Specify which artifacts require digest-only, signature, provenance, and/or SBOM checks by trust profile.
- [ ] `INV11-MC-17-003` Verify artifact bytes before parsing whenever artifact packaging permits.
- [ ] `INV11-MC-17-004` Bind signature verification to the exact artifact digest and expected identity/version.
- [ ] `INV11-MC-17-005` Validate signer trust roots/identities using explicit configuration; never accept any valid signature indiscriminately.
- [ ] `INV11-MC-17-006` Support expiry/revocation/status policy where the selected signing technology provides it.
- [ ] `INV11-MC-17-007` Verify provenance subject digest, builder identity, source reference, build parameters, and predicate type according to policy.
- [ ] `INV11-MC-17-008` Validate SBOM association to the same release artifact and capture its digest.
- [ ] `INV11-MC-17-009` Fail closed on malformed verification metadata, unsupported algorithms, ambiguous subjects, or policy mismatch.
- [ ] `INV11-MC-17-010` Return structured verification evidence distinct from parse/compatibility results.
- [ ] `INV11-MC-17-011` Cache verification only by immutable artifact digest plus trust-policy version.
- [ ] `INV11-MC-17-012` Emit stable diagnostics without leaking secret key material or credentials.
- [ ] `INV11-MC-17-013` Create fixtures for valid, invalid, expired/revoked if supported, wrong-subject, wrong-identity, and tampered artifacts.
- [ ] `INV11-MC-17-014` Test verification behavior in offline mode with pinned trust material.
- [ ] `INV11-MC-17-015` Document trust bootstrapping and key/root rotation procedures.
- [ ] `INV11-MC-17-016` Surface verified provenance status in release acceptance evidence and audit events.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-17-017` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-17-018` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-17-019` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-17-020` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-17-021` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-17-022` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-17-023` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-17-024` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-17-025` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-17-026` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-17-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Signed artifact/provenance verification hook` as production-ready for its declared scope.

---

# 18. Supported-version compatibility matrix

**Priority:** P1  
**Component ID:** `INV11-MC-18`  
**Objective:** Publish and enforce an explicit matrix covering INV-11 tool versions, WIT feature levels, runtime/component-model versions, schemas, normalization policies, and adjacent subsystem versions.

**Primary dependencies:** Components 1–9; Components 19,22,33,34.  
**Required deliverables:** Version matrix; Enforcement helper; Upgrade/downgrade policy; Deprecation schedule; Matrix tests.

## Component-specific implementation checklist

- [ ] `INV11-MC-18-001` Enumerate every independently versioned dimension that can affect semantics or interoperability.
- [ ] `INV11-MC-18-002` Define minimum, maximum, preferred, and unsupported ranges for each dimension.
- [ ] `INV11-MC-18-003` Distinguish parse support from full compatibility-classification support.
- [ ] `INV11-MC-18-004` Distinguish experimental features from production-supported features.
- [ ] `INV11-MC-18-005` Map each INV-11 release to supported PK_INTERFACE/PK_INTERFACE_DIFF schema versions.
- [ ] `INV11-MC-18-006` Map each release to normalization and compatibility-policy versions.
- [ ] `INV11-MC-18-007` Record supported pk_core API/package versions and adjacent INV/GAP integration versions.
- [ ] `INV11-MC-18-008` Define behavior when input declares a future/unknown feature level: explicit refusal or controlled parse-only mode.
- [ ] `INV11-MC-18-009` Implement a programmatic matrix check at public boundaries rather than relying only on documentation.
- [ ] `INV11-MC-18-010` Emit structured mismatch diagnostics containing requested and supported ranges.
- [ ] `INV11-MC-18-011` Add tests for every matrix boundary and at least one version below/above each supported range.
- [ ] `INV11-MC-18-012` Require matrix update during any dependency/toolchain version bump.
- [ ] `INV11-MC-18-013` Document upgrade and downgrade paths and any one-way migrations.
- [ ] `INV11-MC-18-014` Tie deprecation dates/grace periods to the lifecycle manager.
- [ ] `INV11-MC-18-015` Publish the matrix in both human-readable and machine-readable forms.
- [ ] `INV11-MC-18-016` Include the active matrix/version tuple in acceptance evidence.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-18-017` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-18-018` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-18-019` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-18-020` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-18-021` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-18-022` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-18-023` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-18-024` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-18-025` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-18-026` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-18-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Supported-version compatibility matrix` as production-ready for its declared scope.

---

# 19. Adjacent-layer integration tests

**Priority:** P1  
**Component ID:** `INV11-MC-19`  
**Objective:** Prove INV-11 contracts interoperate correctly with INV-09 portable compute ISA, INV-10 composition, INV-12 language interoperability, and GAP-15 runtime certification without absorbing their responsibilities.

**Primary dependencies:** Components 8,9,18; External adjacent components.  
**Required deliverables:** Integration harness; Boundary contracts; Cross-component fixtures; Failure-injection tests; Versioned compatibility matrix.

## Component-specific implementation checklist

- [ ] `INV11-MC-19-001` Document the exact owned/non-owned boundary between INV-11 and each adjacent subsystem.
- [ ] `INV11-MC-19-002` Define typed adapter interfaces and machine-readable payloads exchanged at each boundary.
- [ ] `INV11-MC-19-003` Create minimal healthy end-to-end fixture for INV-09 identity/capability interaction.
- [ ] `INV11-MC-19-004` Create composition/linking fixture exercising INV-10 without implementing linker behavior inside INV-11.
- [ ] `INV11-MC-19-005` Create cross-language fixture path through INV-12 that consumes INV-11 normalized contracts.
- [ ] `INV11-MC-19-006` Create runtime-certification fixture proving GAP-15 can consume contract/evidence outputs.
- [ ] `INV11-MC-19-007` Test version mismatch and unsupported feature errors at every boundary.
- [ ] `INV11-MC-19-008` Test malformed adjacent payloads and verify fail-closed schema validation.
- [ ] `INV11-MC-19-009` Inject timeouts, missing dependencies, partial evidence, and corrupted artifacts.
- [ ] `INV11-MC-19-010` Ensure adjacent failures are attributed to the correct subsystem in diagnostics.
- [ ] `INV11-MC-19-011` Record component versions and digests in integration evidence.
- [ ] `INV11-MC-19-012` Run integration tests against pinned known-good versions and selected next-version candidates before upgrade.
- [ ] `INV11-MC-19-013` Avoid shared mutable global state between adapters.
- [ ] `INV11-MC-19-014` Add contract tests that can run with stubs when full adjacent repositories are unavailable.
- [ ] `INV11-MC-19-015` Define release gate policy for blocked integration tests so missing dependencies cannot produce false green results.
- [ ] `INV11-MC-19-016` Publish integration ownership and escalation contacts in component metadata.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-19-017` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-19-018` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-19-019` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-19-020` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-19-021` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-19-022` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-19-023` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-19-024` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-19-025` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-19-026` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-19-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Adjacent-layer integration tests` as production-ready for its declared scope.

---

# 20. Cross-language conformance fixtures

**Priority:** P1  
**Component ID:** `INV11-MC-20`  
**Objective:** Demonstrate that supported producer/consumer languages interpret the same WIT contracts and compatibility semantics equivalently across bindings and runtime boundaries.

**Primary dependencies:** Components 1–10; INV-12 language interoperability; Component 18 matrix.  
**Required deliverables:** Language fixture set; Generated/handwritten bindings; Canonical observed-behavior assertions; Interop harness; Language support matrix.

## Component-specific implementation checklist

- [ ] `INV11-MC-20-001` Define the initial supported language/runtime set and exact compiler/toolchain versions.
- [ ] `INV11-MC-20-002` Select representative contract shapes: scalars, strings, lists, records, variants, enums, flags, options, results, tuples, resources, and errors.
- [ ] `INV11-MC-20-003` Create producer/consumer pairs in both directions for each supported language pair where practical.
- [ ] `INV11-MC-20-004` Use generated bindings only when generator version is pinned and its output is treated as test input, not as INV-11-owned functionality.
- [ ] `INV11-MC-20-005` Verify parameter/result ordering and nested type interpretation at runtime.
- [ ] `INV11-MC-20-006` Verify Unicode/string and integer-width boundary behavior relevant to contract interpretation.
- [ ] `INV11-MC-20-007` Verify resource ownership/borrowing semantics with lifecycle assertions.
- [ ] `INV11-MC-20-008` Verify error/result propagation and variant discriminants.
- [ ] `INV11-MC-20-009` Include compatibility migration fixtures where one side uses old contract and the other uses an allowed new contract.
- [ ] `INV11-MC-20-010` Include expected-failure fixtures for breaking migrations.
- [ ] `INV11-MC-20-011` Record compiler, binding generator, runtime, platform, and artifact digests.
- [ ] `INV11-MC-20-012` Separate language-mapping defects from INV-11 classification defects in triage.
- [ ] `INV11-MC-20-013` Run smoke subset per change and complete language matrix for releases.
- [ ] `INV11-MC-20-014` Document unsupported language-specific features and mapping caveats.
- [ ] `INV11-MC-20-015` Retain binary/artifact reproduction steps without checking in opaque untraceable binaries where source builds are possible.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-20-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-20-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-20-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-20-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-20-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-20-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-20-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-20-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-20-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-20-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-20-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Cross-language conformance fixtures` as production-ready for its declared scope.

---

# 21. Explicit package/build metadata

**Priority:** P2  
**Component ID:** `INV11-MC-21`  
**Objective:** Turn the Python implementation into a reproducibly buildable, installable package with explicit interpreter constraints, dependencies, package data, and build behavior.

**Primary dependencies:** Component 22 pk_core dependency; Component 23 CI.  
**Required deliverables:** pyproject.toml; Build backend configuration; Package-data declaration; Wheel/sdist tests; Metadata validation.

## Component-specific implementation checklist

- [ ] `INV11-MC-21-001` Create standards-compliant pyproject.toml with project name, version source, description, license, authors/maintainers as appropriate, and Python requirement.
- [ ] `INV11-MC-21-002` Choose and pin/constraint the build backend according to project policy.
- [ ] `INV11-MC-21-003` Declare runtime, optional test, lint, fuzz, and integration dependencies in explicit groups/extras.
- [ ] `INV11-MC-21-004` Package required non-Python assets such as schemas, fixtures, and version data deliberately.
- [ ] `INV11-MC-21-005` Exclude audit scratch files, caches, secrets, and local build artifacts from distributions.
- [ ] `INV11-MC-21-006` Use a single source of truth for package version and verify VERSION/package metadata agree.
- [ ] `INV11-MC-21-007` Declare supported Python versions based on actual CI coverage, not assumption.
- [ ] `INV11-MC-21-008` Build wheel and sdist in a clean environment.
- [ ] `INV11-MC-21-009` Install each artifact into a fresh environment and run standalone unit tests.
- [ ] `INV11-MC-21-010` Check package imports without pk_core for the dependency-free model path.
- [ ] `INV11-MC-21-011` Check expected failure/actionable diagnostic when pk_core-backed paths are invoked without the dependency.
- [ ] `INV11-MC-21-012` Validate metadata with packaging tooling and fail on warnings treated as release blockers.
- [ ] `INV11-MC-21-013` Inspect artifact contents and licenses before release.
- [ ] `INV11-MC-21-014` Document editable-development and release-build commands.
- [ ] `INV11-MC-21-015` Include artifact digests in release evidence.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-21-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-21-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-21-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-21-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-21-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-21-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-21-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-21-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-21-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-21-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-21-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Explicit package/build metadata` as production-ready for its declared scope.

---

# 22. Resolvable pk_core dependency declaration

**Priority:** P2  
**Component ID:** `INV11-MC-22`  
**Objective:** Replace path-only discovery with a reproducible, versioned, documented pk_core dependency contract while retaining explicit standalone-model behavior.

**Primary dependencies:** Component 18 version matrix; Component 21 packaging.  
**Required deliverables:** Dependency declaration; Supported version range; Adapter boundary; Offline resolution instructions; Dependency conformance tests.

## Component-specific implementation checklist

- [ ] `INV11-MC-22-001` Identify the authoritative pk_core package/repository/artifact source and ownership.
- [ ] `INV11-MC-22-002` Define the exact API surface INV-11 consumes from pk_core.
- [ ] `INV11-MC-22-003` Declare a compatible pk_core version/range in package metadata or deployment lock files.
- [ ] `INV11-MC-22-004` Pin exact versions for release builds even if development allows a range.
- [ ] `INV11-MC-22-005` Remove implicit sys.path/path probing from production execution paths where possible.
- [ ] `INV11-MC-22-006` Keep dependency-free interface_model imports functional without pk_core installation.
- [ ] `INV11-MC-22-007` Implement a small adapter layer so pk_core API changes are localized.
- [ ] `INV11-MC-22-008` Validate pk_core version at adapter initialization and emit a clear mismatch diagnostic.
- [ ] `INV11-MC-22-009` Add contract tests using the minimum and maximum supported pk_core versions.
- [ ] `INV11-MC-22-010` Add a test that confirms conformance runner fails closed when pk_core is missing.
- [ ] `INV11-MC-22-011` Document installation for online and offline/air-gapped environments.
- [ ] `INV11-MC-22-012` Record pk_core package/artifact digest in release evidence and SBOM.
- [ ] `INV11-MC-22-013` Define upgrade review procedure for pk_core major/minor changes.
- [ ] `INV11-MC-22-014` Add fallback stubs only for isolated tests; never silently use them in production conformance runs.
- [ ] `INV11-MC-22-015` Document ownership/escalation path for pk_core compatibility failures.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-22-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-22-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-22-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-22-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-22-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-22-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-22-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-22-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-22-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-22-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-22-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Resolvable pk_core dependency declaration` as production-ready for its declared scope.

---

# 23. CI pipeline

**Priority:** P2  
**Component ID:** `INV11-MC-23`  
**Objective:** Establish non-bypassable automated gates for build, tests, static analysis, security checks, fuzz smoke, packaging, and release evidence generation.

**Primary dependencies:** Components 10–22; Components 24–32.  
**Required deliverables:** CI workflow; Gate policy; Artifact retention; Matrix strategy; Release job.

## Component-specific implementation checklist

- [ ] `INV11-MC-23-001` Run on every pull/merge request and protected default-branch change.
- [ ] `INV11-MC-23-002` Use least-privilege CI permissions and pin third-party actions/tools by immutable digest or approved version policy.
- [ ] `INV11-MC-23-003` Matrix-test all supported Python versions and required operating systems.
- [ ] `INV11-MC-23-004` Run syntax/compile checks and dependency-free unit tests first for fast failure.
- [ ] `INV11-MC-23-005` Run full pk_core conformance only when the declared dependency is present; missing dependency must fail required jobs, not skip green.
- [ ] `INV11-MC-23-006` Run compatibility corpus, schema validation, integration smoke, and optimized-mode tests.
- [ ] `INV11-MC-23-007` Run strict static typing and lint checks with zero unreviewed errors.
- [ ] `INV11-MC-23-008` Run dependency/security scanning and secret scanning according to policy.
- [ ] `INV11-MC-23-009` Run bounded fuzz-smoke and property tests with deterministic seed reporting.
- [ ] `INV11-MC-23-010` Build wheel/sdist/release ZIP in a clean job and test-install artifacts.
- [ ] `INV11-MC-23-011` Generate SHA-256 manifest, SBOM, provenance metadata, and evidence bundle.
- [ ] `INV11-MC-23-012` Run reproducibility comparison where supported.
- [ ] `INV11-MC-23-013` Upload logs/test reports/artifacts with defined retention and no secrets.
- [ ] `INV11-MC-23-014` Use required status checks and branch protection to prevent manual bypass without an audited exception.
- [ ] `INV11-MC-23-015` Separate untrusted pull-request execution from jobs holding signing credentials.
- [ ] `INV11-MC-23-016` Create release jobs that sign only previously tested immutable artifacts.
- [ ] `INV11-MC-23-017` Publish a machine-readable gate summary with pass/fail/not-run reasons.
- [ ] `INV11-MC-23-018` Periodically test CI failure paths so skipped/missing-tool conditions cannot appear green.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-23-019` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-23-020` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-23-021` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-23-022` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-23-023` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-23-024` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-23-025` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-23-026` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-23-027` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-23-028` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-23-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `CI pipeline` as production-ready for its declared scope.

---

# 24. Static type-checking configuration

**Priority:** P2  
**Component ID:** `INV11-MC-24`  
**Objective:** Enforce strict, maintainable typing across compatibility logic and explicit adapter boundaries to reduce ambiguous data states and runtime-only defects.

**Primary dependencies:** Components 2,21–23.  
**Required deliverables:** Type-checker config; Typed public API; Adapter protocols; Type CI gate; Typing regression tests.

## Component-specific implementation checklist

- [ ] `INV11-MC-24-001` Select and pin the project type checker and strictness profile.
- [ ] `INV11-MC-24-002` Enable strict checks for interface_model, metadata, parser/resolver core, and schema models first.
- [ ] `INV11-MC-24-003` Annotate every public function, method, dataclass field, and protocol boundary.
- [ ] `INV11-MC-24-004` Use precise tuple/sequence/mapping types that preserve semantic ordering guarantees.
- [ ] `INV11-MC-24-005` Model discriminated unions/enums for node kinds and compatibility classes instead of free-form strings.
- [ ] `INV11-MC-24-006` Use Protocol/ABC boundaries for pk_core and external tool adapters.
- [ ] `INV11-MC-24-007` Avoid Any at trust boundaries; where unavoidable, isolate and validate immediately.
- [ ] `INV11-MC-24-008` Type recursive semantic nodes using forward references or dedicated graph IDs safely.
- [ ] `INV11-MC-24-009` Distinguish unresolved and resolved reference types so phases cannot be accidentally mixed.
- [ ] `INV11-MC-24-010` Type structured diagnostics/reason codes and schema DTOs.
- [ ] `INV11-MC-24-011` Enable unreachable/unused-ignore detection where supported.
- [ ] `INV11-MC-24-012` Require documented, narrowly scoped ignores with issue references for unavoidable third-party typing gaps.
- [ ] `INV11-MC-24-013` Run type checking on tests to verify fixture APIs remain aligned.
- [ ] `INV11-MC-24-014` Add regression tests for runtime validation where static typing cannot enforce input correctness.
- [ ] `INV11-MC-24-015` Fail CI on new type errors and track baseline reduction if legacy exemptions remain.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-24-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-24-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-24-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-24-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-24-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-24-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-24-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-24-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-24-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-24-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-24-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Static type-checking configuration` as production-ready for its declared scope.

---

# 25. Lint/security scanning policy

**Priority:** P2  
**Component ID:** `INV11-MC-25`  
**Objective:** Apply reproducible code-quality, secret, dependency, and security analysis with pinned rules and an auditable exception mechanism.

**Primary dependencies:** Components 21–23; Component 35 waiver registry.  
**Required deliverables:** Lint config; Security scanner config; Dependency audit config; Exception registry; CI reports.

## Component-specific implementation checklist

- [ ] `INV11-MC-25-001` Select format/lint/security/dependency scanners and pin their versions.
- [ ] `INV11-MC-25-002` Define formatting and lint rules appropriate for Python 3.x support range.
- [ ] `INV11-MC-25-003` Enable checks for unsafe subprocess use, path traversal, insecure temporary files, unsafe deserialization, weak hashes where security relevant, and shell injection.
- [ ] `INV11-MC-25-004` Enable secret scanning for source and CI configuration.
- [ ] `INV11-MC-25-005` Audit runtime and development dependencies against vulnerability advisories.
- [ ] `INV11-MC-25-006` Define severity thresholds that block CI versus warn.
- [ ] `INV11-MC-25-007` Scan built artifacts/SBOM, not only source lock files.
- [ ] `INV11-MC-25-008` Require each suppression/ignore to include scanner rule ID, rationale, owner, scope, and expiry.
- [ ] `INV11-MC-25-009` Store suppressions in version-controlled configuration rather than inline blanket disables where possible.
- [ ] `INV11-MC-25-010` Prevent scanners from downloading unpinned executable code during protected release jobs.
- [ ] `INV11-MC-25-011` Capture scanner versions and database timestamp/digest in evidence.
- [ ] `INV11-MC-25-012` Fail cleanly when scanners are unavailable; do not convert missing security scans into pass.
- [ ] `INV11-MC-25-013` Add policy tests with intentionally bad sample code/dependency metadata to prove scanners/gates trigger.
- [ ] `INV11-MC-25-014` Review rule set and exceptions on a fixed cadence.
- [ ] `INV11-MC-25-015` Document local developer commands matching CI behavior.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-25-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-25-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-25-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-25-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-25-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-25-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-25-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-25-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-25-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-25-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-25-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Lint/security scanning policy` as production-ready for its declared scope.

---

# 26. Performance benchmark harness

**Priority:** P2  
**Component ID:** `INV11-MC-26`  
**Objective:** Measure parse, resolution, normalization, compatibility classification, and rendering latency/throughput against reproducible datasets and stated p50/p95/p99 targets.

**Primary dependencies:** Components 10,12,15; Component 28 capacity model.  
**Required deliverables:** Benchmark CLI; Dataset manifest; Metric schema; Baseline storage; Regression thresholds.

## Component-specific implementation checklist

- [ ] `INV11-MC-26-001` Define benchmark operations separately: parse, resolve, normalize, fingerprint, diff/classify, render, end-to-end.
- [ ] `INV11-MC-26-002` Define representative small/medium/large datasets with immutable digests.
- [ ] `INV11-MC-26-003` Record machine CPU, memory, OS, Python, tool version, and power/performance mode for each run.
- [ ] `INV11-MC-26-004` Warm up code paths where appropriate and define whether cold-cache metrics are separately measured.
- [ ] `INV11-MC-26-005` Use enough iterations/samples to compute stable p50/p95/p99 and confidence/variance measures.
- [ ] `INV11-MC-26-006` Measure wall time and CPU time; record peak RSS/allocation where practical.
- [ ] `INV11-MC-26-007` Prevent benchmark correctness shortcuts by validating outputs/digests during runs.
- [ ] `INV11-MC-26-008` Separate parser I/O time from pure compute where useful.
- [ ] `INV11-MC-26-009` Establish target/service-level budgets for key dataset classes.
- [ ] `INV11-MC-26-010` Store baseline results in a versioned machine-readable format.
- [ ] `INV11-MC-26-011` Define regression thresholds with noise tolerance and require review for accepted regressions.
- [ ] `INV11-MC-26-012` Run lightweight performance smoke in CI and controlled full benchmarks for releases.
- [ ] `INV11-MC-26-013` Add adversarial but permitted near-limit cases to reveal nonlinear behavior.
- [ ] `INV11-MC-26-014` Profile regressions and link profile artifacts to issues/evidence.
- [ ] `INV11-MC-26-015` Publish benchmark methodology so results are reproducible rather than marketing-only numbers.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-26-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-26-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-26-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-26-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-26-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-26-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-26-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-26-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-26-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-26-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-26-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Performance benchmark harness` as production-ready for its declared scope.

---

# 27. Scale/soak tests

**Priority:** P2  
**Component ID:** `INV11-MC-27`  
**Objective:** Exercise thousands of packages/interfaces and sustained repeated workloads to detect memory leaks, cache pathologies, nondeterminism, and algorithmic hot spots.

**Primary dependencies:** Components 4,7,15,26,28.  
**Required deliverables:** Scale generator/corpus; Soak runner; Memory/latency telemetry; Leak thresholds; Failure reproducer.

## Component-specific implementation checklist

- [ ] `INV11-MC-27-001` Define scale tiers by packages, interfaces, declarations, type nodes, dependency edges, and source bytes.
- [ ] `INV11-MC-27-002` Generate deterministic synthetic graphs with controlled fan-out, depth, SCC size, and duplicate short names.
- [ ] `INV11-MC-27-003` Include real-corpus aggregation tests in addition to synthetic graphs.
- [ ] `INV11-MC-27-004` Run repeated parse/resolve/diff cycles long enough to expose retained references and cache growth.
- [ ] `INV11-MC-27-005` Track RSS, heap/allocation indicators, object counts if available, cache size, throughput, and tail latency over time.
- [ ] `INV11-MC-27-006` Define acceptable steady-state memory growth and fail on sustained unbounded growth.
- [ ] `INV11-MC-27-007` Exercise cache churn with changing dependency versions/fingerprints.
- [ ] `INV11-MC-27-008` Exercise repeated invalid inputs to ensure diagnostic paths do not leak or amplify memory.
- [ ] `INV11-MC-27-009` Test concurrent independent workloads if concurrency is supported, otherwise assert non-thread-safe restrictions explicitly.
- [ ] `INV11-MC-27-010` Use near-limit graphs to validate graceful refusal instead of process failure.
- [ ] `INV11-MC-27-011` Capture minimal seed/configuration for reproducibility of any scale failure.
- [ ] `INV11-MC-27-012` Run soak under optimized mode and at least one supported production platform.
- [ ] `INV11-MC-27-013` Compare results against the capacity model and update either implementation or model when divergence is material.
- [ ] `INV11-MC-27-014` Archive release-qualification scale summaries in the acceptance evidence bundle.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-27-015` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-27-016` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-27-017` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-27-018` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-27-019` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-27-020` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-27-021` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-27-022` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-27-023` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-27-024` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-27-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Scale/soak tests` as production-ready for its declared scope.

---

# 28. Capacity model

**Priority:** P2  
**Component ID:** `INV11-MC-28`  
**Objective:** Document and validate expected computational complexity, memory use, and operational ceilings as functions of source size, symbol count, graph size, recursion, and dependency fan-out.

**Primary dependencies:** Components 4,7,15,26,27.  
**Required deliverables:** Complexity analysis; Sizing formulas; Operational tiers; Validated limits; Capacity guidance.

## Component-specific implementation checklist

- [ ] `INV11-MC-28-001` Define input dimensions: bytes, tokens, declarations, symbols, type nodes, edges, graph depth, SCC size, and diff pair count.
- [ ] `INV11-MC-28-002` Document expected asymptotic time complexity for lexer/parser, resolver, normalization, hashing, and compatibility comparison.
- [ ] `INV11-MC-28-003` Document expected memory complexity and major retained data structures.
- [ ] `INV11-MC-28-004` Identify operations with potential quadratic or worse behavior and the conditions that trigger it.
- [ ] `INV11-MC-28-005` Map hard resource limits to the capacity assumptions they protect.
- [ ] `INV11-MC-28-006` Establish supported workload tiers with expected latency/memory envelopes.
- [ ] `INV11-MC-28-007` Validate formulas empirically using benchmark and scale datasets.
- [ ] `INV11-MC-28-008` Record safety margins between supported normal workloads and hard refusal limits.
- [ ] `INV11-MC-28-009` Include cache memory and cache invalidation behavior in the model.
- [ ] `INV11-MC-28-010` Include diagnostic/output amplification worst cases.
- [ ] `INV11-MC-28-011` Define operator guidance for raising limits, including expected hardware impact.
- [ ] `INV11-MC-28-012` Version the capacity model when algorithms or defaults change.
- [ ] `INV11-MC-28-013` Create regression checks for key slopes, not only single-point performance.
- [ ] `INV11-MC-28-014` Include capacity-model assumptions in release evidence and architecture documentation.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-28-015` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-28-016` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-28-017` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-28-018` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-28-019` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-28-020` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-28-021` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-28-022` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-28-023` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-28-024` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-28-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Capacity model` as production-ready for its declared scope.

---

# 29. Structured telemetry adapter

**Priority:** P2  
**Component ID:** `INV11-MC-29`  
**Objective:** Expose privacy-conscious, vendor-neutral metrics for workload volume, classification outcomes, failures, latency, limits, and saturation without making core correctness depend on telemetry.

**Primary dependencies:** Components 5,15,26; Component 40 ownership.  
**Required deliverables:** Telemetry interface; Metric catalog; No-op adapter; Reference exporter; Cardinality policy.

## Component-specific implementation checklist

- [ ] `INV11-MC-29-001` Define a minimal telemetry protocol decoupled from any specific observability vendor.
- [ ] `INV11-MC-29-002` Provide a no-op implementation with near-zero overhead for standalone/offline use.
- [ ] `INV11-MC-29-003` Define counters for parses, resolutions, classifications, link refusals, validation failures, and limit refusals.
- [ ] `INV11-MC-29-004` Define histograms/timers for parse, resolve, normalize, diff, and end-to-end latency.
- [ ] `INV11-MC-29-005` Define gauges for cache size, in-flight work, graph sizes, or queue depth only where meaningful.
- [ ] `INV11-MC-29-006` Use bounded low-cardinality labels; never label metrics with raw package names, paths, source text, or arbitrary identifiers by default.
- [ ] `INV11-MC-29-007` Separate error classes using stable diagnostic/reason codes only where cardinality remains bounded.
- [ ] `INV11-MC-29-008` Document units and aggregation semantics for every metric.
- [ ] `INV11-MC-29-009` Ensure telemetry failures never alter compatibility results or crash the core engine.
- [ ] `INV11-MC-29-010` Support explicit sampling/configuration for high-volume events.
- [ ] `INV11-MC-29-011` Add tests asserting metric emission for success, refusal, parse failure, and limit-exceeded paths.
- [ ] `INV11-MC-29-012` Add performance tests for telemetry overhead.
- [ ] `INV11-MC-29-013` Define privacy/redaction expectations for any trace/log integration.
- [ ] `INV11-MC-29-014` Expose active tool/policy version as resource metadata rather than high-cardinality per-event labels.
- [ ] `INV11-MC-29-015` Document mapping to the organization’s observability stack as an adapter concern.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-29-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-29-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-29-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-29-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-29-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-29-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-29-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-29-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-29-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-29-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-29-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Structured telemetry adapter` as production-ready for its declared scope.

---

# 30. Tamper-evident audit-event emitter

**Priority:** P2  
**Component ID:** `INV11-MC-30`  
**Objective:** Produce durable, append-oriented security and release decision events bound to artifact fingerprints, policy versions, actors/services, and prior event state.

**Primary dependencies:** Components 16,17,29,35,38.  
**Required deliverables:** Audit event schema; Hash-chain/signature option; Emitter interface; Storage adapter; Verification utility.

## Component-specific implementation checklist

- [ ] `INV11-MC-30-001` Define which decisions are audit-worthy: release gate, compatibility refusal/override, waiver, provenance failure, signing, and policy change.
- [ ] `INV11-MC-30-002` Create a versioned event schema with event ID, timestamp, actor/service identity, action, subject fingerprint, policy version, result, and reason codes.
- [ ] `INV11-MC-30-003` Use trusted time source expectations explicitly; do not treat timestamps alone as integrity proof.
- [ ] `INV11-MC-30-004` Bind events to immutable subject fingerprints rather than mutable file paths.
- [ ] `INV11-MC-30-005` Implement tamper evidence via hash chaining, signed batches, or approved external append-only log integration.
- [ ] `INV11-MC-30-006` Separate audit events from high-volume operational telemetry.
- [ ] `INV11-MC-30-007` Define sensitive-field redaction and prohibit raw source/secret material by default.
- [ ] `INV11-MC-30-008` Make emitter failure policy explicit for critical release/security events: fail closed or spool durably according to deployment profile.
- [ ] `INV11-MC-30-009` Provide idempotency/deduplication handling for retried event writes.
- [ ] `INV11-MC-30-010` Implement verification tooling that detects deletion, reordering, modification, or chain breaks where the chosen scheme supports it.
- [ ] `INV11-MC-30-011` Add tests for valid chains, tampering, truncation, replay, duplicate IDs, and storage failure.
- [ ] `INV11-MC-30-012` Define retention, access control, export, and incident-review procedures.
- [ ] `INV11-MC-30-013` Link waiver/exception events to registry entries and evidence bundles.
- [ ] `INV11-MC-30-014` Record audit schema and verification-tool versions in release documentation.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-30-015` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-30-016` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-30-017` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-30-018` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-30-019` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-30-020` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-30-021` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-30-022` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-30-023` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-30-024` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-30-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Tamper-evident audit-event emitter` as production-ready for its declared scope.

---

# 31. Release signing and SBOM generation

**Priority:** P2  
**Component ID:** `INV11-MC-31`  
**Objective:** Ship each release with verifiable signatures/attestations, a dependency/material inventory, provenance, digests, and documented verification instructions.

**Primary dependencies:** Components 16,17,21–23,32.  
**Required deliverables:** Signed release artifact; SBOM; Provenance statement; Digest manifest; Verification guide.

## Component-specific implementation checklist

- [ ] `INV11-MC-31-001` Select approved signing/attestation mechanism and document signer identity/trust-root policy.
- [ ] `INV11-MC-31-002` Protect signing credentials from pull-request/untrusted CI contexts and use least privilege.
- [ ] `INV11-MC-31-003` Sign or attest the exact immutable release artifacts produced by the gated build.
- [ ] `INV11-MC-31-004` Generate cryptographic digest manifest for every distributed artifact.
- [ ] `INV11-MC-31-005` Generate SBOM in an approved standard format including direct/transitive dependencies and relevant build materials.
- [ ] `INV11-MC-31-006` Include package versions, hashes, licenses where available, and component relationships in the SBOM.
- [ ] `INV11-MC-31-007` Generate provenance containing source revision, builder identity, build recipe/workflow, parameters, and artifact subject digests.
- [ ] `INV11-MC-31-008` Ensure SBOM/provenance subjects match the signed release digest exactly.
- [ ] `INV11-MC-31-009` Publish verification commands that work in a clean environment.
- [ ] `INV11-MC-31-010` Test signature verification and negative tamper cases before release publication.
- [ ] `INV11-MC-31-011` Define key/root rotation and compromised-signer response procedures.
- [ ] `INV11-MC-31-012` Define retention/access for historical verification material.
- [ ] `INV11-MC-31-013` Include signing/SBOM/provenance checks in the acceptance evidence bundle.
- [ ] `INV11-MC-31-014` Never regenerate metadata for an already published binary without clearly creating a new attestation/release record.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-31-015` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-31-016` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-31-017` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-31-018` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-31-019` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-31-020` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-31-021` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-31-022` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-31-023` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-31-024` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-31-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Release signing and SBOM generation` as production-ready for its declared scope.

---

# 32. Reproducible-build procedure

**Priority:** P2  
**Component ID:** `INV11-MC-32`  
**Objective:** Make release artifacts deterministically rebuildable from pinned source and dependencies, and detect nondeterminism through byte-for-byte or semantically defined comparison.

**Primary dependencies:** Components 21–23,31.  
**Required deliverables:** Pinned build recipe; Deterministic archive tool/config; Rebuild verifier; Nondeterminism log; Repro instructions.

## Component-specific implementation checklist

- [ ] `INV11-MC-32-001` Pin source revision, Python/runtime versions, build backend, dependencies, and build tools.
- [ ] `INV11-MC-32-002` Set/normalize timestamps, archive entry ordering, permissions, owner/group metadata, and path separators.
- [ ] `INV11-MC-32-003` Remove host-specific absolute paths, temp directories, usernames, and nondeterministic UUIDs from artifacts.
- [ ] `INV11-MC-32-004` Ensure generated manifests/schemas have deterministic key/file ordering.
- [ ] `INV11-MC-32-005` Set reproducible locale/timezone/environment variables where tool behavior depends on them.
- [ ] `INV11-MC-32-006` Build in a clean isolated environment at least twice and compare artifacts.
- [ ] `INV11-MC-32-007` Prefer byte-for-byte equality; where a format prevents it, define a documented canonical semantic comparison.
- [ ] `INV11-MC-32-008` Identify and document each unavoidable nondeterministic field and mitigation plan.
- [ ] `INV11-MC-32-009` Verify wheel, sdist, hardened ZIP, SBOM, and provenance subject digests as applicable.
- [ ] `INV11-MC-32-010` Keep signing separate from reproducibility comparison because signatures may intentionally include time/identity material.
- [ ] `INV11-MC-32-011` Add a CI/release job that rebuilds from source and reports digest differences.
- [ ] `INV11-MC-32-012` Provide a diff tool/report showing which archive members or metadata differ.
- [ ] `INV11-MC-32-013` Publish exact local reproduction steps and required tool versions.
- [ ] `INV11-MC-32-014` Treat unexplained nondeterminism as a release blocker.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-32-015` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-32-016` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-32-017` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-32-018` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-32-019` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-32-020` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-32-021` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-32-022` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-32-023` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-32-024` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-32-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Reproducible-build procedure` as production-ready for its declared scope.

---

# 33. Semantic-version recommendation engine

**Priority:** P3  
**Component ID:** `INV11-MC-33`  
**Objective:** Optionally map a completed structural compatibility diff to a recommended semantic-version change without allowing version strings to determine compatibility.

**Primary dependencies:** Component 8 compatibility rules; Component 18 matrix; Component 34 lifecycle manager.  
**Required deliverables:** Recommendation policy; Recommendation API; Reason mapping; Policy tests; Override semantics.

## Component-specific implementation checklist

- [ ] `INV11-MC-33-001` Define recommendation outputs such as none/patch/minor/major/indeterminate without modifying the underlying compatibility class.
- [ ] `INV11-MC-33-002` Document the policy mapping from specific diff/reason categories to recommendation levels.
- [ ] `INV11-MC-33-003` Keep recommendations directional and package-scope aware.
- [ ] `INV11-MC-33-004` Handle multiple simultaneous changes by deterministic severity aggregation.
- [ ] `INV11-MC-33-005` Define behavior for documentation/metadata-only changes outside semantic contract structure.
- [ ] `INV11-MC-33-006` Return indeterminate when policy lacks enough semantic information rather than guessing.
- [ ] `INV11-MC-33-007` Include the policy version and contributing reason codes in each recommendation.
- [ ] `INV11-MC-33-008` Allow organization policy overlays only through explicit configuration with separate versioning.
- [ ] `INV11-MC-33-009` Never mark a breaking structural change compatible because the declared version increased.
- [ ] `INV11-MC-33-010` Never mark a structurally compatible change breaking solely because a version string appears unexpected.
- [ ] `INV11-MC-33-011` Add fixture tests for each recommendation mapping and mixed-change aggregation.
- [ ] `INV11-MC-33-012` Add tests proving version-string edits alone do not change structural classification.
- [ ] `INV11-MC-33-013` Integrate deprecation/removal state only through explicit lifecycle metadata.
- [ ] `INV11-MC-33-014` Expose recommendation as advisory data in human/machine diff output, not as hidden enforcement.
- [ ] `INV11-MC-33-015` Document how maintainers can override package versions while preserving the recorded recommendation/evidence.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-33-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-33-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-33-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-33-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-33-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-33-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-33-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-33-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-33-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-33-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-33-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Semantic-version recommendation engine` as production-ready for its declared scope.

---

# 34. Deprecation lifecycle manager

**Priority:** P3  
**Component ID:** `INV11-MC-34`  
**Objective:** Track declared deprecations from announcement through grace period, consumer discovery, enforcement, and removal readiness with auditable gates.

**Primary dependencies:** Components 3,8,18,33,35.  
**Required deliverables:** Deprecation metadata schema; Lifecycle state machine; Deadline/grace policy; Consumer evidence hooks; Removal gate.

## Component-specific implementation checklist

- [ ] `INV11-MC-34-001` Define deprecation states and allowed transitions, including proposed, active, grace, removal-eligible, removed, and cancelled if needed.
- [ ] `INV11-MC-34-002` Attach deprecation metadata to stable qualified symbol identities.
- [ ] `INV11-MC-34-003` Record announcement release/date, rationale, replacement/migration path, owner, and target removal criteria.
- [ ] `INV11-MC-34-004` Define grace period policy in releases/time and how exceptions are handled.
- [ ] `INV11-MC-34-005` Integrate consumer discovery from available dependency/evidence sources without assuming perfect global visibility.
- [ ] `INV11-MC-34-006` Distinguish no observed consumers from proven no consumers.
- [ ] `INV11-MC-34-007` Emit warnings for deprecated use with stable diagnostic codes and source paths.
- [ ] `INV11-MC-34-008` Add policy checks preventing removal before required grace/consumer gates unless an approved waiver exists.
- [ ] `INV11-MC-34-009` Model renamed/replacement APIs explicitly so migration guidance can be generated.
- [ ] `INV11-MC-34-010` Handle package/version branches without losing lifecycle history.
- [ ] `INV11-MC-34-011` Audit all lifecycle transitions and waivers.
- [ ] `INV11-MC-34-012` Add tests for each valid and invalid state transition.
- [ ] `INV11-MC-34-013` Include lifecycle status in human-readable diffs and evidence bundles.
- [ ] `INV11-MC-34-014` Define expiration behavior for stale deprecations that never progress.
- [ ] `INV11-MC-34-015` Document operator workflow and ownership responsibilities.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-34-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-34-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-34-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-34-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-34-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-34-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-34-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-34-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-34-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-34-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-34-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Deprecation lifecycle manager` as production-ready for its declared scope.

---

# 35. Compatibility waiver/exception registry

**Priority:** P3  
**Component ID:** `INV11-MC-35`  
**Objective:** Provide a tightly governed registry for intentional compatibility or release-policy exceptions with owner, rationale, scope, expiry, evidence, and audit linkage.

**Primary dependencies:** Components 30,34,38,40.  
**Required deliverables:** Waiver schema; Registry storage/API; Approval workflow; Expiry enforcement; Audit integration.

## Component-specific implementation checklist

- [ ] `INV11-MC-35-001` Define waiver types and prohibit a generic unrestricted “ignore all” exception.
- [ ] `INV11-MC-35-002` Require exact subject scope using package/world/interface/symbol identity and relevant fingerprint(s).
- [ ] `INV11-MC-35-003` Require affected rule/diagnostic IDs and the specific gate being overridden.
- [ ] `INV11-MC-35-004` Require business/technical rationale, risk assessment, compensating controls, owner, approver, and issue/change reference.
- [ ] `INV11-MC-35-005` Require creation and expiration timestamps or release bounds; disallow non-expiring waivers by default.
- [ ] `INV11-MC-35-006` Bind waivers to policy/tool version so rule changes trigger reevaluation.
- [ ] `INV11-MC-35-007` Prevent wildcard scope from expanding automatically to future symbols/versions unless explicitly designed and approved.
- [ ] `INV11-MC-35-008` Validate waiver authenticity/integrity and access controls in shared environments.
- [ ] `INV11-MC-35-009` Apply waivers after detection so underlying failures remain visible in evidence.
- [ ] `INV11-MC-35-010` Emit an audit event whenever a waiver is created, modified, used, expires, or is revoked.
- [ ] `INV11-MC-35-011` Fail closed on malformed, expired, ambiguous, or subject-mismatched waivers.
- [ ] `INV11-MC-35-012` Provide reports of active/expiring/expired waivers and usage frequency.
- [ ] `INV11-MC-35-013` Add tests for scope boundaries, expiry, fingerprint mismatch, policy-version mismatch, and revocation.
- [ ] `INV11-MC-35-014` Include used waivers in acceptance evidence with no secret/sensitive notes exposed unnecessarily.
- [ ] `INV11-MC-35-015` Define periodic review cadence and escalation for repeatedly renewed exceptions.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-35-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-35-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-35-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-35-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-35-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-35-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-35-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-35-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-35-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-35-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-35-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Compatibility waiver/exception registry` as production-ready for its declared scope.

---

# 36. Adapter/shim generation for supported compatible migrations

**Priority:** P3  
**Component ID:** `INV11-MC-36`  
**Objective:** Generate narrow adapters only for transformations proven semantics-preserving by explicit rules, while refusing migrations that require business logic or lossy interpretation.

**Primary dependencies:** Components 8,10,20,33.  
**Required deliverables:** Eligibility rules; Adapter IR/templates; Generator; Validation harness; Refusal diagnostics.

## Component-specific implementation checklist

- [ ] `INV11-MC-36-001` Define a closed allowlist of migration patterns eligible for automatic adaptation.
- [ ] `INV11-MC-36-002` Start with trivial structurally provable cases; do not infer semantic defaults from names or comments.
- [ ] `INV11-MC-36-003` Represent adapter plans in a machine-readable intermediate form before generating code.
- [ ] `INV11-MC-36-004` Bind adapter plans to source and target contract fingerprints and compatibility-policy version.
- [ ] `INV11-MC-36-005` Generate only for explicitly supported language/runtime targets through pluggable backends.
- [ ] `INV11-MC-36-006` Require explicit values/defaults only when they are encoded in a trusted policy or schema; never invent them.
- [ ] `INV11-MC-36-007` Refuse narrowing numeric conversions, dropped required fields, unknown variant mapping, ownership changes, or other lossy transformations.
- [ ] `INV11-MC-36-008` Preserve error/result semantics and resource ownership/lifetime.
- [ ] `INV11-MC-36-009` Generate clear diagnostics explaining why an adapter cannot be safely generated.
- [ ] `INV11-MC-36-010` Compile/type-check generated adapters in supported toolchains.
- [ ] `INV11-MC-36-011` Run cross-language/runtime conformance tests comparing adapted behavior with canonical expected behavior.
- [ ] `INV11-MC-36-012` Use deterministic generation so identical inputs produce identical source artifacts.
- [ ] `INV11-MC-36-013` Include source/target fingerprints and generator version in generated-file headers/metadata.
- [ ] `INV11-MC-36-014` Security-scan and lint generated output.
- [ ] `INV11-MC-36-015` Treat generated adapters as optional migration aids, not evidence that a structurally breaking change is compatible.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-36-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-36-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-36-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-36-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-36-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-36-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-36-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-36-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-36-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-36-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-36-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Adapter/shim generation for supported compatible migrations` as production-ready for its declared scope.

---

# 37. Human-readable diff renderer

**Priority:** P3  
**Component ID:** `INV11-MC-37`  
**Objective:** Render compatibility changes in concise and expanded forms grouped by canonical package/world/interface/type/function paths while retaining exact machine-readable reason linkage.

**Primary dependencies:** Components 5,8,9,33–36.  
**Required deliverables:** Concise renderer; Expanded renderer; Stable grouping/sorting; CLI/text format; Golden snapshots.

## Component-specific implementation checklist

- [ ] `INV11-MC-37-001` Consume structured diff/reason objects; never re-derive compatibility from text.
- [ ] `INV11-MC-37-002` Group output hierarchically by package, world, interface, declaration, and nested path.
- [ ] `INV11-MC-37-003` Use deterministic ordering identical across runs/platforms.
- [ ] `INV11-MC-37-004` Show overall classification separately from per-change classifications.
- [ ] `INV11-MC-37-005` Distinguish additions, removals, renames/moves if known, type changes, ordering changes, and policy warnings.
- [ ] `INV11-MC-37-006` Display old/new type/signature forms using a canonical compact renderer.
- [ ] `INV11-MC-37-007` Provide concise summary mode for CI and expanded mode with rationale/remediation hints.
- [ ] `INV11-MC-37-008` Show stable reason/diagnostic codes so prose can change without breaking automation.
- [ ] `INV11-MC-37-009` Show deprecation, waiver, and semantic-version recommendation annotations without hiding underlying structural changes.
- [ ] `INV11-MC-37-010` Avoid dumping entire large graphs; summarize with bounded detail and explicit truncation notices.
- [ ] `INV11-MC-37-011` Support plain text and optionally structured terminal formatting without making color necessary for meaning.
- [ ] `INV11-MC-37-012` Respect path/source redaction configuration.
- [ ] `INV11-MC-37-013` Add golden snapshot tests for representative complex diffs and Unicode identifiers.
- [ ] `INV11-MC-37-014` Test width/narrow-terminal behavior if a CLI surface is provided.
- [ ] `INV11-MC-37-015` Document that machine consumers must use PK_INTERFACE_DIFF schema rather than scraping rendered text.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-37-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-37-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-37-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-37-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-37-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-37-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-37-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-37-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-37-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-37-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-37-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Human-readable diff renderer` as production-ready for its declared scope.

---

# 38. Machine-readable acceptance evidence bundle

**Priority:** P3  
**Component ID:** `INV11-MC-38`  
**Objective:** Assemble a signed/digest-bound release evidence package linking requirements, tests, benchmarks, provenance, matrices, waivers, and gate verdicts to the exact release artifact.

**Primary dependencies:** Components 9,16,17,23,26,30,31,35.  
**Required deliverables:** Evidence schema; Bundle assembler; Artifact references/digests; Gate summary; Verification procedure.

## Component-specific implementation checklist

- [ ] `INV11-MC-38-001` Define a versioned evidence manifest/schema with a unique release/evidence identity.
- [ ] `INV11-MC-38-002` Reference the exact release artifact, source revision, and all relevant fingerprints/digests.
- [ ] `INV11-MC-38-003` Include tool, normalization, compatibility-policy, schema, feature-level, and dependency versions.
- [ ] `INV11-MC-38-004` Link requirements/checklist IDs to test cases and their pass/fail/not-run results.
- [ ] `INV11-MC-38-005` Include unit, corpus, differential, integration, property, fuzz-smoke, optimized-mode, and packaging gate summaries.
- [ ] `INV11-MC-38-006` Include benchmark results and capacity/limit configuration used for qualification.
- [ ] `INV11-MC-38-007` Include SBOM/provenance/signature verification status.
- [ ] `INV11-MC-38-008` Include active and used waivers with identifiers, scope, expiry, and approval references.
- [ ] `INV11-MC-38-009` Represent blocked/not-run gates explicitly; never coerce missing evidence to pass.
- [ ] `INV11-MC-38-010` Include audit-event anchors or log references where appropriate.
- [ ] `INV11-MC-38-011` Use relative/content-addressed references or embedded small records so bundles remain portable.
- [ ] `INV11-MC-38-012` Protect integrity through bundle digest/signature/attestation as approved.
- [ ] `INV11-MC-38-013` Provide a verifier that checks schema, digests, signatures, and subject consistency.
- [ ] `INV11-MC-38-014` Add tests for tampered artifacts, missing evidence, conflicting versions, expired waivers, and malformed manifests.
- [ ] `INV11-MC-38-015` Keep raw secrets/credentials and unnecessary source content out of the bundle.
- [ ] `INV11-MC-38-016` Define retention and historical reproducibility expectations for released evidence.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-38-017` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-38-018` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-38-019` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-38-020` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-38-021` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-38-022` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-38-023` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-38-024` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-38-025` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-38-026` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-38-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Machine-readable acceptance evidence bundle` as production-ready for its declared scope.

---

# 39. Architecture decision record (ADR)

**Priority:** P3  
**Component ID:** `INV11-MC-39`  
**Objective:** Capture approved architectural choices for language scope, parser/tool strategy, identity, normalization, compatibility philosophy, trust boundaries, and rejected alternatives.

**Primary dependencies:** All P0 design components; Component 18 matrix; Component 40 ownership.  
**Required deliverables:** ADR document(s); Decision status/owners; Alternatives analysis; Consequences; Review triggers.

## Component-specific implementation checklist

- [ ] `INV11-MC-39-001` Record context and problem statement for INV-11 as an interface-contract compatibility subsystem.
- [ ] `INV11-MC-39-002` State the exact WIT/component-model scope and authoritative specification/tool references.
- [ ] `INV11-MC-39-003` Document the decision to keep language binding generation, linking, runtime marshalling, language mapping, and placement outside INV-11 unless separately approved.
- [ ] `INV11-MC-39-004` Document parser strategy: native implementation, library integration, or hybrid, with rationale.
- [ ] `INV11-MC-39-005` Document syntax AST versus semantic model separation decision.
- [ ] `INV11-MC-39-006` Document nominal identity and package/version resolution philosophy.
- [ ] `INV11-MC-39-007` Document canonical normalization and fingerprinting approach.
- [ ] `INV11-MC-39-008` Document compatibility directionality and fail-closed behavior for unknown constructs.
- [ ] `INV11-MC-39-009` Document dependency/provenance trust model for imported contracts.
- [ ] `INV11-MC-39-010` Document resource-limit/security posture for untrusted input.
- [ ] `INV11-MC-39-011` Compare rejected alternatives with technical pros/cons and migration implications.
- [ ] `INV11-MC-39-012` Record operational consequences: dependencies, build complexity, performance, and support burden.
- [ ] `INV11-MC-39-013` Record decision owners, approval date, status, and superseding ADR links.
- [ ] `INV11-MC-39-014` Define triggers requiring ADR review, such as grammar major version, policy reclassification, or resolver model change.
- [ ] `INV11-MC-39-015` Link implementation components/tests that realize each key decision so architecture drift is detectable.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-39-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-39-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-39-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-39-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-39-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-39-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-39-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-39-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-39-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-39-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-39-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Architecture decision record (ADR)` as production-ready for its declared scope.

---

# 40. Ownership/escalation metadata

**Priority:** P3  
**Component ID:** `INV11-MC-40`  
**Objective:** Make operational accountability explicit for code, schemas, compatibility policy, releases, security incidents, waivers, and end-of-life decisions.

**Primary dependencies:** Components 18,30,34,35,38,39.  
**Required deliverables:** Ownership manifest; Review cadence; Escalation matrix; Service/support expectations; EOL policy.

## Component-specific implementation checklist

- [ ] `INV11-MC-40-001` Assign accountable owner/team for parser, semantic model, resolver, compatibility policy, schemas, release pipeline, and security response.
- [ ] `INV11-MC-40-002` Assign backup/escalation contacts/roles to avoid single-person ownership.
- [ ] `INV11-MC-40-003` Define review/approval requirements for compatibility-rule changes, schema changes, and version-matrix changes.
- [ ] `INV11-MC-40-004` Define response ownership for parser security findings, provenance/signing incidents, and corrupted releases.
- [ ] `INV11-MC-40-005` Define operational severity levels and escalation paths without embedding private contact details in public artifacts unless intended.
- [ ] `INV11-MC-40-006` Define release authority and emergency rollback/yank authority.
- [ ] `INV11-MC-40-007` Define waiver approvers and separation-of-duties expectations for high-risk exceptions.
- [ ] `INV11-MC-40-008` Define routine review cadence for dependencies, version matrix, limits, waivers, and deprecated APIs.
- [ ] `INV11-MC-40-009` Define support window for each major/minor release line.
- [ ] `INV11-MC-40-010` Define EOL notice period, final supported versions, and archival/verification obligations.
- [ ] `INV11-MC-40-011` Define ownership transfer procedure when teams/repositories change.
- [ ] `INV11-MC-40-012` Store ownership metadata in a machine-readable file plus human-readable documentation.
- [ ] `INV11-MC-40-013` Validate required ownership fields in CI.
- [ ] `INV11-MC-40-014` Link ownership roles into audit events and acceptance evidence where actions require accountability.
- [ ] `INV11-MC-40-015` Review ownership/escalation metadata at every major release and after organizational changes.

## Cross-cutting engineering and acceptance checklist

- [ ] `INV11-MC-40-016` **Requirements & traceability:** Assign stable requirement IDs to the component and map each implementation task to at least one automated or reviewable acceptance artifact.
- [ ] `INV11-MC-40-017` **API/versioning:** Define public interfaces, configuration schema, versioning rules, and backward-compatibility expectations before declaring the component stable.
- [ ] `INV11-MC-40-018` **Failure semantics:** Define fail-open versus fail-closed behavior for every external dependency, malformed input, timeout, limit breach, and unsupported feature; security/correctness boundaries should fail closed.
- [ ] `INV11-MC-40-019` **Determinism:** Verify repeated execution with identical inputs/configuration produces identical semantic outputs, classifications, reason ordering, and fingerprints where applicable.
- [ ] `INV11-MC-40-020` **Security review:** Threat-model untrusted input, path/process boundaries, deserialization, resource exhaustion, dependency trust, and information disclosure relevant to this component.
- [ ] `INV11-MC-40-021` **Unit/integration tests:** Provide automated positive, negative, boundary, and regression tests; required tests must not silently skip and report success.
- [ ] `INV11-MC-40-022` **Performance/capacity:** Measure or bound the component’s CPU, memory, I/O, and output amplification at representative and near-limit workloads.
- [ ] `INV11-MC-40-023` **Documentation:** Document operator/developer usage, configuration defaults, limitations, troubleshooting, and examples synchronized with the implementation.
- [ ] `INV11-MC-40-024` **Evidence:** Emit or contribute machine-readable release evidence identifying tool version, configuration/policy version, tests performed, and artifact/input fingerprints.
- [ ] `INV11-MC-40-025` **Definition of done:** Do not mark complete until code review, security/quality gates, tests, documentation, version metadata, and release evidence all pass with no unexplained skips.

## Component acceptance gate

- [ ] `INV11-MC-40-GATE` All checklist requirements above are closed or covered by approved waiver records; required automated tests pass with no false-green skips; artifacts are versioned; documentation and release evidence identify `Ownership/escalation metadata` as production-ready for its declared scope.

---

# Program-level readiness gates

These gates are intentionally separate from the 40 component gates so INV-11 cannot be called production-complete merely because individual workstreams are locally green.

- [ ] `INV11-PROGRAM-001` All P0 components (1–10) pass their component acceptance gates.
- [ ] `INV11-PROGRAM-002` P0 policy behavior is covered by a versioned fixture corpus with no undocumented compatibility-rule gaps.
- [ ] `INV11-PROGRAM-003` Required P1 hostile-input and interoperability gates (11–20) pass against the supported-version matrix.
- [ ] `INV11-PROGRAM-004` Parser/schema fuzzing has no unresolved release-blocking crashes, hangs, resource-limit bypasses, or validation bypasses.
- [ ] `INV11-PROGRAM-005` Differential testing has no unreviewed divergence from the pinned authoritative toolchain.
- [ ] `INV11-PROGRAM-006` Cross-language and adjacent-layer integration tests pass for every production-supported matrix cell.
- [ ] `INV11-PROGRAM-007` P2 build, CI, security, benchmark, soak, telemetry, audit, signing/SBOM, and reproducibility gates are operational and required in release qualification.
- [ ] `INV11-PROGRAM-008` Release artifacts install and execute in clean supported environments and preserve the dependency-free structural model behavior.
- [ ] `INV11-PROGRAM-009` Required `pk_core` conformance runs against a resolvable supported dependency; absence or mismatch is reported as blocked/failure, never a passing skipped suite.
- [ ] `INV11-PROGRAM-010` Capacity model and configured resource limits are validated against release benchmark/scale results.
- [ ] `INV11-PROGRAM-011` Every distributed release artifact has verified digest, SBOM, provenance, and required signature/attestation.
- [ ] `INV11-PROGRAM-012` Reproducible-build verification passes or every remaining nondeterministic field has a reviewed documented exception.
- [ ] `INV11-PROGRAM-013` P3 lifecycle controls are active for supported long-lived production contracts: semver recommendation, deprecation, waivers, adapters where safe, human diff, evidence bundle, ADR, and ownership.
- [ ] `INV11-PROGRAM-014` External/non-goal responsibilities remain explicitly separated: binding generation, component linking, runtime marshalling, language-specific type mapping, and placement are integrated/tested but not silently absorbed into INV-11.
- [ ] `INV11-PROGRAM-015` A machine-readable acceptance evidence bundle ties the final release artifact to all required requirements, tests, tool versions, policy/schema/normalization versions, benchmarks, provenance, and any waivers.
- [ ] `INV11-PROGRAM-016` Final architecture/security/release review records a production GO/NO-GO decision for the declared scope and supported-version matrix.

## Recommended implementation sequence

1. Complete P0 components 1–10 in dependency order, with the parser/AST/identity/resolver/diagnostics foundation preceding full compatibility policy.
2. Build the P1 assurance layer 11–20, beginning with corpora and differential/property/fuzz infrastructure, then version/interoperability integration.
3. Establish P2 packaging/CI/type/security gates early enough that P0/P1 work is continuously enforced, then finish benchmarks, telemetry, auditability, signing, and reproducibility.
4. Add P3 lifecycle/governance features after the structural policy and evidence formats are stable enough to govern long-term evolution.
5. Do not declare INV-11 production-complete until all program-level readiness gates required by the intended deployment profile are satisfied.
