# INV-09 Portable Compute ISA v4.2.0 — Production Missing-Components Engineering Checklist

**Source gap register:** `MISSING_COMPONENTS.md` from the INV-09 v4.2.0 audit  
**Scope:** 52 missing production components, priorities P0–P3  
**Purpose:** implementation, security hardening, verification, operations, and production-exit tracking  
**Status semantics:** unchecked items are not evidence of implementation; each item requires objective linked evidence before PASS.

## Checklist conventions

- **P0:** required before INV-09 can be treated as a production WebAssembly validation boundary.
- **P1:** security, determinism, compatibility, and host-capability controls required for production assurance.
- **P2:** reliability, performance, observability, rollout, and recoverability controls.
- **P3:** packaging, governance, traceability, ownership, and formal production release controls.
- **Evidence rule:** a checkbox is PASS only when the linked artifact is current for the exact validator/profile/spec/engine/release scope being certified.
- **Waiver rule:** WAIVED is not PASS. It requires M51 approval, compensating controls, exact scope, owner, and expiration; M52 must evaluate it explicitly.
- **Security rule:** any condition that could allow a false ACCEPT, execution without current validation, evidence replay/misbinding, or unsafe mixed configuration is fail-closed by default.

## Cross-component dependency sequence

1. **Trustworthy semantic foundation:** M01 → M02 → M03, governed by M05 and M13.
2. **Artifact/policy identity:** M04 + M07 + M22 + M25 → M08.
3. **Execution enforcement:** M06 + M08 + M09 + M11 + M24 → M10.
4. **Correctness assurance:** M12 + M14 + M15 + M16 + M20 + M21.
5. **Host/component capability layers:** M17 + M18 + optional M19, integrated through M23.
6. **Production operations:** M26–M44.
7. **Supply chain/governance:** M45–M51.
8. **Final production decision:** M48 + all required current evidence → M52.

## M01 — Raw Wasm binary decoder and structural validator [P0]

**Objective:** Decode untrusted WebAssembly module bytes and establish trustworthy structural facts before any higher-level policy decision.
**Primary dependencies/interfaces:** M05, M12, M13, M14, M15
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M01-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Raw Wasm binary decoder and structural validator**; record escalation paths in M50.
- [ ] **M01-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M01-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M01-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M01-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M01-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M01-007** — Implement strict magic/version parsing and reject trailing/leading ambiguity before section decoding.
- [ ] **M01-008** — Decode every standard section with canonical unsigned/signed LEB128 handling, overflow checks, truncation checks, and minimal-encoding policy where required.
- [ ] **M01-009** — Enforce section ordering, singleton-section uniqueness, custom-section handling, declared payload lengths, and exact payload consumption.
- [ ] **M01-010** — Validate index spaces and cross-section bounds for types, functions, tables, memories, globals, tags, elements, data, imports, and exports.
- [ ] **M01-011** — Reject integer overflow/underflow in size arithmetic before allocation, slicing, multiplication, or offset addition.
- [ ] **M01-012** — Apply hard ceilings while decoding names, vectors, nested block structure, section counts, and aggregate bytes rather than after parse completion.
- [ ] **M01-013** — Preserve byte offsets and section context for every parsed construct so downstream errors can identify exact evidence locations.
- [ ] **M01-014** — Expose an immutable parsed-module representation that cannot be mutated by policy callers after structural validation.
- [ ] **M01-015** — Define treatment of unknown future sections/opcodes as fail-closed unless explicitly enabled by the pinned specification registry.
- [ ] **M01-016** — Ensure parser state cannot desynchronize after malformed lengths, unterminated LEB128 values, or invalid UTF-8 names.
- [ ] **M01-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M01-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M01-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M01-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M01-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M01-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M01-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M01-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M01-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M01-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M01-027** — Golden-test known-valid minimal and multi-section modules.
- [ ] **M01-028** — Reject bad magic, unsupported version, truncated section headers, oversized payload lengths, duplicate singleton sections, and out-of-order standard sections.
- [ ] **M01-029** — Exercise malformed/overlong LEB128, integer-wrap boundaries, zero-length edge cases, and vector-count bombs.
- [ ] **M01-030** — Run coverage-guided fuzzing with sanitizer/instrumented builds where applicable and retain every unique crash/rejection discrepancy as a regression seed.
- [ ] **M01-031** — Differentially parse the same corpus with at least two mature independent Wasm implementations and investigate every semantic disagreement.
- [ ] **M01-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M01-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M01-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M01-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M01-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M01-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M01-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M01-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M01-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M01-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M01-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M01-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M01-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M01-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M01-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M01-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M01-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M01-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M01-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M01-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M01-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M01: 52 items.**

## M02 — Wasm type validator [P0]

**Objective:** Prove that structurally decoded modules satisfy WebAssembly typing, stack, control-flow, index, and proposal-specific validation rules.
**Primary dependencies/interfaces:** M01, M05, M13, M14, M15
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M02-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Wasm type validator**; record escalation paths in M50.
- [ ] **M02-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M02-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M02-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M02-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M02-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M02-007** — Implement function-body validation with an explicit typed operand stack and control-frame stack matching the pinned core specification semantics.
- [ ] **M02-008** — Validate block/loop/if signatures, branch depths, branch value arity, unreachable-polymorphic stack behavior, return typing, and end-of-block stack shape.
- [ ] **M02-009** — Validate local/global declarations, mutability constraints, constant-expression rules, and global initialization dependencies.
- [ ] **M02-010** — Validate call/call_indirect targets, function/table type compatibility, reference types, element expressions, and table constraints.
- [ ] **M02-011** — Validate memory instructions, alignment immediates, memory indices, memory64/multi-memory rules when enabled, and data-segment references.
- [ ] **M02-012** — Validate imports/exports for duplicate names, legal external kinds, type compatibility, limits, and index-space construction.
- [ ] **M02-013** — Gate proposal-specific typing rules through M05 rather than scattering ad-hoc feature checks throughout the validator.
- [ ] **M02-014** — Produce deterministic failure codes for type mismatch, stack underflow, invalid branch, invalid index, invalid limits, invalid constant expression, and unsupported proposal.
- [ ] **M02-015** — Avoid recursion proportional to attacker-controlled nesting unless bounded by M13; prefer iterative validation for deeply nested expressions.
- [ ] **M02-016** — Return immutable typed facts required by feature detection and admission without trusting caller-supplied descriptors.
- [ ] **M02-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M02-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M02-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M02-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M02-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M02-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M02-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M02-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M02-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M02-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M02-027** — Run official/spec-derived positive and negative validation fixtures for every enabled instruction family.
- [ ] **M02-028** — Create mutation tests that alter one type/index/immediate at a time and assert rejection at the expected byte offset.
- [ ] **M02-029** — Test unreachable code, nested control flow, multi-value blocks, reference types, SIMD, bulk memory, and other enabled proposals at boundary conditions.
- [ ] **M02-030** — Differentially compare valid/invalid verdicts against independent production runtimes for the certified feature set.
- [ ] **M02-031** — Verify optimized/release builds produce identical verdicts and failure codes to debug/test builds.
- [ ] **M02-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M02-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M02-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M02-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M02-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M02-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M02-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M02-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M02-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M02-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M02-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M02-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M02-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M02-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M02-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M02-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M02-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M02-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M02-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M02-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M02-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M02: 52 items.**

## M03 — Byte-derived feature detector [P0]

**Objective:** Derive the exact WebAssembly feature set from validated module bytes and parsed semantics instead of manifests or caller assertions.
**Primary dependencies/interfaces:** M01, M02, M05, M12
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M03-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Byte-derived feature detector**; record escalation paths in M50.
- [ ] **M03-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M03-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M03-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M03-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M03-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M03-007** — Define a canonical feature-ID taxonomy with one stable identifier per proposal/capability used by profiles, logs, attestations, and policy.
- [ ] **M03-008** — Map every feature-sensitive opcode, type form, section field, limits form, segment mode, and encoding variant to one or more feature IDs.
- [ ] **M03-009** — Detect features from the trusted AST/IR produced by M01/M02, never directly from untrusted declared metadata.
- [ ] **M03-010** — Distinguish syntactic presence from semantic requirement where a construct can be encoded without being executed.
- [ ] **M03-011** — Define implication rules such as proposal A requiring baseline feature B, and compute a canonical transitive closure.
- [ ] **M03-012** — Return a sorted/normalized immutable set to make digests and attestations reproducible.
- [ ] **M03-013** — Fail closed when a decoded construct lacks a registry mapping or is associated with an unrecognized proposal revision.
- [ ] **M03-014** — Record byte offset/section evidence for each detected feature so M37 can explain why it was required.
- [ ] **M03-015** — Ensure custom sections cannot spoof feature detection unless a specific authenticated convention is intentionally supported.
- [ ] **M03-016** — Provide a registry consistency check proving no enabled parser/type-validator branch lacks a feature classification.
- [ ] **M03-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M03-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M03-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M03-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M03-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M03-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M03-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M03-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M03-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M03-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M03-027** — Create one minimal fixture per recognized feature and assert exact detection with no extras.
- [ ] **M03-028** — Create mixed-feature modules and verify stable canonical ordering and transitive implications.
- [ ] **M03-029** — Mutate declarations while keeping bytes fixed and prove detected features do not change.
- [ ] **M03-030** — Add negative tests for unknown opcodes/types and assert fail-closed behavior.
- [ ] **M03-031** — Cross-check detected features with independent tooling for a broad real-world corpus.
- [ ] **M03-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M03-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M03-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M03-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M03-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M03-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M03-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M03-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M03-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M03-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M03-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M03-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M03-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M03-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M03-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M03-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M03-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M03-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M03-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M03-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M03-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M03: 52 items.**

## M04 — Declared-capability source and binding rule [P0]

**Objective:** Define, authenticate, and cryptographically bind declared module capabilities to the exact module artifact they authorize.
**Primary dependencies/interfaces:** M07, M08, M22, M25
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M04-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Declared-capability source and binding rule**; record escalation paths in M50.
- [ ] **M04-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M04-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M04-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M04-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M04-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M04-007** — Select the authoritative declaration container and schema; prohibit ambiguous precedence between manifest, registry metadata, signatures, and embedded custom sections.
- [ ] **M04-008** — Define canonical serialization for capability declarations so identical content always yields identical bytes for signing/hashing.
- [ ] **M04-009** — Bind declarations to M07 module digest, profile/schema revision, issuer identity, and validity window in the signed payload.
- [ ] **M04-010** — Require signature verification and trust-chain evaluation before declarations can influence validation.
- [ ] **M04-011** — Define issuer authorization: which principals may declare which capabilities for which tenant/workload namespace.
- [ ] **M04-012** — Reject detached/replayed declarations whose module digest, tenant, profile, or validity period does not match the current request.
- [ ] **M04-013** — Define declaration downgrade/upgrade semantics and require explicit re-signing whenever capabilities change.
- [ ] **M04-014** — Separate “declared” from “detected/used” features and require used ⊆ declared ⊆ profile-permitted.
- [ ] **M04-015** — Record declaration digest and signer identity in M08 validation attestation and M27 audit events.
- [ ] **M04-016** — Specify revocation and emergency invalidation for compromised signing identities or mis-issued declarations.
- [ ] **M04-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M04-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M04-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M04-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M04-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M04-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M04-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M04-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M04-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M04-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M04-027** — Verify tampering with any declaration byte, module byte, profile binding, tenant binding, or timestamp invalidates authorization.
- [ ] **M04-028** — Test replay of a valid declaration against a different module with the same filename/path and require rejection.
- [ ] **M04-029** — Test conflicting declaration sources and assert deterministic precedence or outright rejection according to the contract.
- [ ] **M04-030** — Test expired, not-yet-valid, revoked, untrusted, and wrong-tenant signatures.
- [ ] **M04-031** — Generate conformance fixtures for canonical serialization and signature verification across independent implementations.
- [ ] **M04-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M04-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M04-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M04-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M04-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M04-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M04-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M04-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M04-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M04-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M04-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M04-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M04-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M04-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M04-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M04-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M04-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M04-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M04-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M04-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M04-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M04: 52 items.**

## M05 — Specification/version registry [P0]

**Objective:** Provide the authoritative, versioned mapping between supported WebAssembly specifications/proposals and concrete binary constructs/features.
**Primary dependencies/interfaces:** M01, M02, M03, M06, M21, M22
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M05-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Specification/version registry**; record escalation paths in M50.
- [ ] **M05-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M05-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M05-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M05-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M05-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M05-007** — Create a machine-readable registry schema containing specification family, proposal ID, revision/commit, status, feature ID, opcode/type/section mappings, dependencies, and incompatibilities.
- [ ] **M05-008** — Pin exact normative references or immutable revision identifiers; do not use floating labels such as “latest”.
- [ ] **M05-009** — Represent baseline/core semantics separately from optional proposals and from WASI/component-model layers.
- [ ] **M05-010** — Validate registry integrity at build/startup: unique IDs, no overlapping opcode encodings for the same decoding context, resolved dependencies, and known schema version.
- [ ] **M05-011** — Sign registry releases and verify signatures before activation through M43.
- [ ] **M05-012** — Generate parser/type-validator lookup tables from the registry where feasible to reduce hand-maintained drift.
- [ ] **M05-013** — Define deprecation, supersession, and withdrawal mechanics without silently changing old profile meaning.
- [ ] **M05-014** — Expose a stable registry digest/revision used by M08 attestations, M09 cache keys, M33 health, and M35 logs.
- [ ] **M05-015** — Add compatibility metadata tying each feature revision to certified runtime engine capabilities in M06.
- [ ] **M05-016** — Require code review and architecture approval for any new proposal activation.
- [ ] **M05-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M05-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M05-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M05-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M05-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M05-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M05-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M05-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M05-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M05-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M05-027** — Schema-validate every registry artifact and reject unknown/duplicate fields according to policy.
- [ ] **M05-028** — Generate coverage tests proving every recognized parser token/opcode/type has exactly one governed mapping.
- [ ] **M05-029** — Replay historical registries to ensure old attestations remain interpretable.
- [ ] **M05-030** — Test attempted downgrade to an older vulnerable/unsupported registry revision.
- [ ] **M05-031** — Compare generated feature mappings against independent spec fixtures and proposal test suites.
- [ ] **M05-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M05-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M05-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M05-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M05-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M05-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M05-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M05-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M05-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M05-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M05-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M05-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M05-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M05-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M05-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M05-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M05-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M05-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M05-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M05-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M05-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M05: 52 items.**

## M06 — Engine capability registry [P0]

**Objective:** Describe what each approved runtime/engine build actually implements so policy never admits a module the selected engine cannot safely execute.
**Primary dependencies/interfaces:** M05, M21, M24, M41
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M06-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Engine capability registry**; record escalation paths in M50.
- [ ] **M06-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M06-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M06-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M06-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M06-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M06-007** — Define engine identity as vendor/project, exact version/build hash, compilation options, target architecture, OS ABI, and relevant runtime flags.
- [ ] **M06-008** — Record supported feature IDs and exact proposal revisions using M05 identifiers rather than free-form strings.
- [ ] **M06-009** — Record known-disabled, experimental, unsafe, or non-deterministic engine features independently of parser support.
- [ ] **M06-010** — Capture engine security posture metadata: sandbox mode, JIT/AOT mode, executable-memory policy, mitigations, and minimum security patch level.
- [ ] **M06-011** — Support deny/revoke markers for engine versions affected by critical CVEs or semantic miscompilations.
- [ ] **M06-012** — Sign registry entries and bind them to release artifacts/build provenance.
- [ ] **M06-013** — Require admission to intersect profile-permitted features, byte-detected features, and engine-supported features.
- [ ] **M06-014** — Expose registry revision/digest to cache keys, attestations, health checks, and compatibility matrices.
- [ ] **M06-015** — Model architecture-dependent capability differences explicitly rather than assuming one engine version behaves identically everywhere.
- [ ] **M06-016** — Define lifecycle ownership and update SLA when a runtime release or security advisory changes capability claims.
- [ ] **M06-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M06-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M06-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M06-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M06-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M06-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M06-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M06-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M06-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M06-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M06-027** — Probe each certified engine build with generated feature fixtures and compare measured support to declared registry support.
- [ ] **M06-028** — Test admission rejection when one required feature is absent or revoked in the selected engine entry.
- [ ] **M06-029** — Test architecture-specific differences and ensure the wrong target entry cannot be selected.
- [ ] **M06-030** — Test registry tampering, unsigned entries, stale revisions, and emergency revocation propagation.
- [ ] **M06-031** — Continuously reconcile registry claims with M21 certification results.
- [ ] **M06-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M06-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M06-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M06-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M06-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M06-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M06-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M06-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M06-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M06-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M06-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M06-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M06-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M06-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M06-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M06-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M06-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M06-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M06-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M06-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M06-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M06: 52 items.**

## M07 — Canonical module digest [P0]

**Objective:** Create a stable cryptographic identity for the exact module bytes used across validation, provenance, caching, attestation, and execution.
**Primary dependencies/interfaces:** M08, M09, M10, M11, M25
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M07-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Canonical module digest**; record escalation paths in M50.
- [ ] **M07-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M07-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M07-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M07-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M07-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M07-007** — Define digest input as the exact immutable module byte sequence; document whether any container/envelope bytes are in or out of scope.
- [ ] **M07-008** — Use an approved collision-resistant algorithm and encode algorithm + digest explicitly to permit controlled future agility.
- [ ] **M07-009** — Stream hashing for large modules so digesting does not require a duplicate full-buffer allocation.
- [ ] **M07-010** — Compute the digest as early as practical and propagate it as the sole artifact identity across the request lifecycle.
- [ ] **M07-011** — Never substitute filename, URL, mutable object ID, timestamp, or metadata as module identity.
- [ ] **M07-012** — Define canonical textual encoding (for example lowercase hex) and reject non-canonical alternate forms at trust boundaries.
- [ ] **M07-013** — Bind size and, where useful, source provenance identifiers to evidence while keeping the digest authoritative for bytes.
- [ ] **M07-014** — Protect digest objects from accidental truncation in logs, caches, database keys, or API serialization.
- [ ] **M07-015** — Support hash algorithm migration with dual-hash transition rules rather than silently reinterpreting identifiers.
- [ ] **M07-016** — Make digest verification mandatory after any transfer/materialization step before execution admission.
- [ ] **M07-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M07-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M07-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M07-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M07-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M07-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M07-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M07-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M07-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M07-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M07-027** — Verify one-bit changes produce distinct identities and invalidate prior cache/attestation hits.
- [ ] **M07-028** — Test streaming vs one-shot hashing equality across empty, tiny, boundary, and maximum-size modules.
- [ ] **M07-029** — Test canonical parser rejection of malformed, truncated, wrong-algorithm, and mixed-case/noncanonical identifiers if prohibited.
- [ ] **M07-030** — Exercise hash migration fixtures with old and new algorithms side by side.
- [ ] **M07-031** — Verify digest used at M10 execution exactly matches the digest attested by M08.
- [ ] **M07-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M07-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M07-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M07-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M07-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M07-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M07-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M07-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M07-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M07-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M07-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M07-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M07-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M07-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M07-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M07-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M07-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M07-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M07-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M07-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M07-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M07: 52 items.**

## M08 — Validation-result attestation [P0]

**Objective:** Produce signed, tamper-evident evidence binding a validation verdict to exact module, validator, policy, specification, engine, and time/sequence context.
**Primary dependencies/interfaces:** M04, M05, M06, M07, M22, M25, M27
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M08-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Validation-result attestation**; record escalation paths in M50.
- [ ] **M08-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M08-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M08-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M08-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M08-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M08-007** — Define a versioned attestation schema with module digest, verdict, detected features, declared capabilities, validator build, policy/profile revision, spec registry digest, engine registry entry, limits revision, and timestamps/sequence.
- [ ] **M08-008** — Include stable failure codes and sanitized evidence for rejected modules without leaking secrets or attacker-controlled log injection.
- [ ] **M08-009** — Use canonical serialization prior to signing; verify the canonical bytes are unambiguous across implementations.
- [ ] **M08-010** — Sign with managed workload/service identity keys protected by the platform key-management boundary; record key ID and algorithm.
- [ ] **M08-011** — Define freshness semantics and maximum acceptable age for admission tokens.
- [ ] **M08-012** — Bind tenant/workload namespace and intended execution environment when attestations are not globally reusable.
- [ ] **M08-013** — Support verifier-side trust roots, key rotation, revocation, and historical verification.
- [ ] **M08-014** — Make attestations append-only/tamper-evident in M27 or an evidence ledger when required by assurance level.
- [ ] **M08-015** — Prohibit transformation of a REJECT result into an ACCEPT token by downstream services; use a signed enum/boolean with schema validation.
- [ ] **M08-016** — Version the schema independently from validator code and define backward-compatible verifier behavior.
- [ ] **M08-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M08-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M08-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M08-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M08-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M08-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M08-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M08-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M08-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M08-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M08-027** — Tamper every signed field in turn and require verification failure.
- [ ] **M08-028** — Test expired, future-dated, revoked-key, wrong-tenant, wrong-engine, and wrong-module attestations.
- [ ] **M08-029** — Test deterministic canonical serialization with multiple language implementations.
- [ ] **M08-030** — Verify admission rejects unsigned or unverifiable tokens even when the embedded verdict says ACCEPT.
- [ ] **M08-031** — Test key rotation and historical verification across retained attestations.
- [ ] **M08-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M08-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M08-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M08-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M08-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M08-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M08-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M08-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M08-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M08-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M08-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M08-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M08-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M08-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M08-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M08-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M08-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M08-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M08-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M08-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M08-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M08: 52 items.**

## M09 — Validation cache with safe invalidation [P0]

**Objective:** Cache validation results without allowing stale policy, specification, engine, or artifact state to create false acceptance.
**Primary dependencies/interfaces:** M05, M06, M07, M08, M22, M42, M43
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M09-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Validation cache with safe invalidation**; record escalation paths in M50.
- [ ] **M09-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M09-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M09-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M09-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M09-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M09-007** — Define a cache key containing module digest plus every verdict-affecting revision: validator build, spec registry, feature profile/policy, engine capability, parser limits, and declaration/provenance inputs.
- [ ] **M09-008** — Store signed M08 attestations or equivalently verifiable records rather than a bare boolean.
- [ ] **M09-009** — Treat ACCEPT and REJECT caching separately; define TTL/retention according to mutation/freshness risks.
- [ ] **M09-010** — Never key by mutable path, URL, filename, tenant-supplied ID, or unverified digest.
- [ ] **M09-011** — Use atomic writes and corruption detection for persistent cache entries.
- [ ] **M09-012** — Namespace tenant-sensitive entries and prevent cross-tenant side channels from hit/miss timing or metadata leakage.
- [ ] **M09-013** — Invalidate by revision change through immutable key variation; avoid broad mutable “current” aliases for security decisions.
- [ ] **M09-014** — Define revocation handling for emergency runtime/spec/profile/key changes that must supersede otherwise-valid cached records.
- [ ] **M09-015** — Bound cache size, entry count, and per-tenant occupancy; implement deterministic eviction that cannot exhaust validator memory/disk.
- [ ] **M09-016** — Instrument hit/miss/stale/corrupt/evicted outcomes with controlled metric cardinality.
- [ ] **M09-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M09-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M09-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M09-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M09-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M09-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M09-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M09-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M09-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M09-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M09-027** — Change each verdict-affecting input independently and prove the previous ACCEPT entry is not reused.
- [ ] **M09-028** — Corrupt serialized cache entries and require revalidation rather than fail-open recovery.
- [ ] **M09-029** — Test concurrent writers/readers for torn writes and mixed revisions.
- [ ] **M09-030** — Test tenant isolation and absence of shared sensitive metadata.
- [ ] **M09-031** — Benchmark hit path, miss path, cache churn, and full-cache eviction under adversarial access patterns.
- [ ] **M09-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M09-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M09-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M09-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M09-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M09-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M09-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M09-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M09-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M09-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M09-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M09-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M09-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M09-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M09-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M09-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M09-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M09-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M09-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M09-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M09-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M09: 52 items.**

## M10 — Execution admission gate [P0]

**Objective:** Make a current, verifiable successful validation result mandatory before any runtime instantiation, compilation, or execution path.
**Primary dependencies/interfaces:** M07, M08, M09, M11, M24, M27
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M10-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Execution admission gate**; record escalation paths in M50.
- [ ] **M10-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M10-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M10-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M10-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M10-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M10-007** — Place the gate at the narrowest runtime choke point that all instantiate/compile/execute entry paths must traverse.
- [ ] **M10-008** — Define an admission request schema carrying module identity, attestation/token, selected runtime/engine identity, tenant/workload context, and execution policy revision.
- [ ] **M10-009** — Verify M08 signature, freshness, module digest, engine binding, profile/policy binding, and tenant scope before passing bytes to the engine.
- [ ] **M10-010** — Deny by default when the validation service, trust store, policy service, or attestation verification dependency is unavailable.
- [ ] **M10-011** — Prohibit debug/admin/API side doors that instantiate raw module bytes without the same gate.
- [ ] **M10-012** — Use capability-based internal APIs so downstream code receives only an admitted immutable module handle, not unrestricted raw bytes.
- [ ] **M10-013** — Emit an audit event for every allow/deny decision and every attempted bypass.
- [ ] **M10-014** — Define explicit behavior for cache hits, revalidation requests, revoked attestations, and profile/engine rotation.
- [ ] **M10-015** — Ensure runtime precompilation/AOT artifact loading is also bound to an admitted source module and certified engine/toolchain.
- [ ] **M10-016** — Provide a hard kill-switch/revocation mechanism that blocks new admissions for compromised validator/runtime revisions.
- [ ] **M10-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M10-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M10-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M10-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M10-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M10-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M10-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M10-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M10-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M10-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M10-027** — Enumerate every runtime entry point and prove with integration tests that unvalidated modules cannot execute.
- [ ] **M10-028** — Present valid tokens with wrong module/tenant/engine/profile and require denial.
- [ ] **M10-029** — Simulate unavailable verifier/policy/cache dependencies and confirm fail-closed behavior.
- [ ] **M10-030** — Attempt direct engine invocation through documented and internal APIs in adversarial tests.
- [ ] **M10-031** — Run end-to-end tests from artifact retrieval through execution and correlate M27 audit evidence.
- [ ] **M10-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M10-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M10-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M10-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M10-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M10-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M10-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M10-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M10-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M10-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M10-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M10-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M10-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M10-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M10-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M10-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M10-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M10-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M10-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M10-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M10-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M10: 52 items.**

## M11 — TOCTOU protection [P0]

**Objective:** Prevent substitution or mutation of module bytes between validation and execution.
**Primary dependencies/interfaces:** M07, M08, M10, M25
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M11-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **TOCTOU protection**; record escalation paths in M50.
- [ ] **M11-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M11-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M11-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M11-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M11-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M11-007** — Adopt immutable content-addressed artifacts or an OS/runtime handle model that pins the validated byte object through execution.
- [ ] **M11-008** — If files are used, avoid validate-by-path then reopen-by-path patterns; validate and execute from the same immutable descriptor/handle when possible.
- [ ] **M11-009** — Recompute/verify M07 digest immediately before compilation/instantiation whenever a byte copy or transfer boundary occurs.
- [ ] **M11-010** — Define immutable storage semantics and deny mutation/overwrite of content-addressed objects.
- [ ] **M11-011** — Bind precompiled/AOT outputs to source digest, compiler/engine build, target architecture, and compilation flags.
- [ ] **M11-012** — Protect against symlink/junction/reparse-point swaps, rename replacement, network-filesystem races, and mutable object-store version aliases.
- [ ] **M11-013** — Use atomic materialization and permission settings that prevent untrusted writers from modifying staged artifacts.
- [ ] **M11-014** — Carry module identity in the admitted handle so downstream components do not recalculate identity from mutable metadata.
- [ ] **M11-015** — Audit every digest mismatch as a security event, not merely a cache miss.
- [ ] **M11-016** — Document platform-specific guarantees and residual risks for Windows, Linux, macOS, containers, and object storage as applicable.
- [ ] **M11-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M11-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M11-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M11-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M11-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M11-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M11-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M11-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M11-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M11-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M11-027** — Race file replacement during validation/admission and prove substituted bytes never execute.
- [ ] **M11-028** — Test symlink/junction/hard-link and rename-swap attacks on supported filesystems.
- [ ] **M11-029** — Mutate staged bytes after attestation creation and require digest verification failure.
- [ ] **M11-030** — Test object-store mutable alias/version changes and require version/digest pinning.
- [ ] **M11-031** — Validate AOT artifact/source binding by mixing artifacts from different source digests.
- [ ] **M11-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M11-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M11-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M11-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M11-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M11-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M11-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M11-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M11-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M11-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M11-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M11-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M11-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M11-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M11-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M11-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M11-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M11-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M11-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M11-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M11-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M11: 52 items.**

## M12 — Structured failure schema [P0]

**Objective:** Provide stable machine-readable failure semantics for parser, type, feature, policy, provenance, admission, and dependency failures.
**Primary dependencies/interfaces:** M01, M02, M03, M10, M35, M37
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M12-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Structured failure schema**; record escalation paths in M50.
- [ ] **M12-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M12-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M12-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M12-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M12-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M12-007** — Define a versioned error envelope with code, category, severity/class, retryability, stage, safe message, module digest, byte offset, section/function context, feature ID, rule ID, and nested cause references as applicable.
- [ ] **M12-008** — Allocate stable error-code namespaces by subsystem and prohibit reusing a retired code for a different meaning.
- [ ] **M12-009** — Separate operator-safe diagnostics from potentially sensitive internal detail and attacker-controlled raw text.
- [ ] **M12-010** — Specify which fields are mandatory for each error category and which may be omitted to avoid fabricated context.
- [ ] **M12-011** — Model multiple failures deterministically when appropriate, including a documented cap and ordering rule.
- [ ] **M12-012** — Ensure invalid inputs never escape as untyped language/runtime exceptions at the service boundary.
- [ ] **M12-013** — Define retryability precisely so policy rejects are not retried while transient dependency failures can be.
- [ ] **M12-014** — Map legacy v4.2.0 exception classes/codes to the new schema for compatibility.
- [ ] **M12-015** — Use schema-generated bindings where feasible and validate responses before emission.
- [ ] **M12-016** — Publish machine-readable documentation and examples for client implementers.
- [ ] **M12-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M12-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M12-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M12-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M12-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M12-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M12-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M12-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M12-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M12-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M12-027** — Schema-test every known failure code and required context field.
- [ ] **M12-028** — Fuzz error construction with attacker-controlled names/custom sections and verify logs/messages cannot inject control sequences or exceed size caps.
- [ ] **M12-029** — Verify clients can round-trip unknown future optional fields without misclassifying the core code.
- [ ] **M12-030** — Test deterministic ordering/capping for modules triggering many independent failures.
- [ ] **M12-031** — Contract-test error mapping through API, logs, traces, attestations, and explain view.
- [ ] **M12-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M12-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M12-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M12-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M12-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M12-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M12-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M12-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M12-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M12-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M12-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M12-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M12-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M12-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M12-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M12-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M12-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M12-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M12-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M12-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M12-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M12: 52 items.**

## M13 — Parser resource governor [P0]

**Objective:** Bound parser/type-validator memory, CPU, recursion/nesting, and structural complexity before attacker-controlled modules can exhaust resources.
**Primary dependencies/interfaces:** M01, M02, M29, M30
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M13-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Parser resource governor**; record escalation paths in M50.
- [ ] **M13-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M13-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M13-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M13-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M13-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M13-007** — Define signed/versioned hard limits for total bytes, section bytes, vector lengths, function count, type count, import/export count, table/memory/global counts, element/data counts, local declarations, name lengths, and custom-section bytes.
- [ ] **M13-008** — Define instruction count, control nesting depth, type-recursion depth, and aggregate validation work budgets.
- [ ] **M13-009** — Charge resource budget before allocation/work, using overflow-safe arithmetic.
- [ ] **M13-010** — Use streaming/iterative parsing where practical to avoid duplicate buffering and unbounded call-stack recursion.
- [ ] **M13-011** — Separate globally safe absolute maxima from profile/tenant-specific quotas; profile limits may tighten but not exceed global hard ceilings without a reviewed release.
- [ ] **M13-012** — Return explicit resource-limit failure codes including which governed dimension was exceeded, without echoing unsafe payload content.
- [ ] **M13-013** — Integrate cancellation/deadline checks at bounded work intervals so timed-out validations terminate promptly.
- [ ] **M13-014** — Enforce per-request and aggregate concurrency budgets to prevent many individually legal modules from exhausting the service.
- [ ] **M13-015** — Ensure decompression/container extraction, if any, has separate zip-bomb/decompression-ratio limits before Wasm parsing.
- [ ] **M13-016** — Version limits and include the active limit revision in M08, M09, M33, and M42.
- [ ] **M13-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M13-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M13-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M13-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M13-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M13-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M13-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M13-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M13-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M13-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M13-027** — Construct one fixture just below and just above every hard limit.
- [ ] **M13-028** — Test integer boundary values that could wrap allocation or work counters.
- [ ] **M13-029** — Generate deep nesting/vector bombs and prove bounded memory/stack use and deterministic rejection.
- [ ] **M13-030** — Load-test concurrent maximum-size modules and assert service-level memory/concurrency limits.
- [ ] **M13-031** — Verify limit revision changes invalidate cached accepts that were evaluated under looser limits.
- [ ] **M13-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M13-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M13-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M13-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M13-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M13-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M13-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M13-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M13-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M13-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M13-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M13-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M13-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M13-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M13-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M13-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M13-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M13-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M13-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M13-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M13-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M13: 52 items.**

## M14 — Fuzzing harness and malformed corpus [P0]

**Objective:** Continuously discover parser/type-validator crashes, hangs, differential errors, and pathological resource behavior using generated malformed and edge-case modules.
**Primary dependencies/interfaces:** M01, M02, M03, M12, M13, M15
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M14-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Fuzzing harness and malformed corpus**; record escalation paths in M50.
- [ ] **M14-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M14-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M14-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M14-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M14-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M14-007** — Provide in-process fuzz targets for raw decoder, section decoders, type validator, feature detector, failure serializer, and end-to-end validation.
- [ ] **M14-008** — Seed with minimal valid modules, proposal-specific fixtures, historical bugs, malformed LEB128, truncations, duplicates, deep control flow, large vectors, and custom-section cases.
- [ ] **M14-009** — Use structure-aware mutation/generation in addition to blind byte mutation so deep semantic states are reached.
- [ ] **M14-010** — Set strict per-input timeout and memory limits and classify crash, OOM, timeout, excessive allocation, and semantic discrepancy separately.
- [ ] **M14-011** — Minimize every interesting input and store it with immutable metadata: discovery build, expected outcome, root cause, fix commit, and regression ID.
- [ ] **M14-012** — Continuously merge upstream/spec test corpora where licensing allows and record provenance.
- [ ] **M14-013** — Run sanitizer/instrumented configurations for native parser components and equivalent runtime diagnostics for managed implementations.
- [ ] **M14-014** — Track edge/branch coverage and corpus growth without treating coverage percentage alone as a soundness metric.
- [ ] **M14-015** — Quarantine nondeterministic fuzz failures until reproduced; never silently discard flaky crash seeds.
- [ ] **M14-016** — Integrate fuzz regression corpus into ordinary CI so fixed failures cannot recur even when fuzzing is not running.
- [ ] **M14-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M14-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M14-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M14-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M14-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M14-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M14-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M14-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M14-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M14-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M14-027** — Demonstrate harness catches injected crash, infinite loop, excessive allocation, and bad-verdict mutants.
- [ ] **M14-028** — Run sustained campaigns against release candidates and archive summary statistics and unique findings.
- [ ] **M14-029** — Verify every historical security bug has a permanent minimized regression fixture.
- [ ] **M14-030** — Test corpus determinism and portability across supported host architectures.
- [ ] **M14-031** — Gate production release on zero unresolved critical/high fuzz crashes or soundness discrepancies.
- [ ] **M14-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M14-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M14-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M14-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M14-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M14-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M14-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M14-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M14-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M14-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M14-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M14-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M14-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M14-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M14-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M14-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M14-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M14-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M14-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M14-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M14-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M14: 52 items.**

## M15 — Differential validation harness [P0]

**Objective:** Detect semantic drift by comparing INV-09 parsing, type validation, and feature classification against independent mature WebAssembly implementations.
**Primary dependencies/interfaces:** M01, M02, M03, M05, M14, M21
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M15-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Differential validation harness**; record escalation paths in M50.
- [ ] **M15-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M15-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M15-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M15-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M15-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M15-007** — Select at least two independent reference implementations with clearly pinned versions/builds and licensing suitable for CI.
- [ ] **M15-008** — Normalize outcomes into comparable classes: parse reject, type reject, feature unsupported, valid, trap-at-runtime not applicable, and implementation error.
- [ ] **M15-009** — Ensure comparisons use equivalent feature/proposal configurations; do not treat a disabled proposal as a semantic disagreement.
- [ ] **M15-010** — Compare byte offsets/diagnostics where useful but base correctness triage primarily on accept/reject semantics and detected feature facts.
- [ ] **M15-011** — Generate reduced reproducers for each disagreement and route them to specification, INV-09, or reference-runtime triage.
- [ ] **M15-012** — Maintain allowlisted known differences with owner, rationale, source/spec citation, affected revisions, and expiration review.
- [ ] **M15-013** — Run against both curated edge cases and a broad real-world corpus.
- [ ] **M15-014** — Include invalid modules from M14 rather than only well-formed ecosystem artifacts.
- [ ] **M15-015** — Record the exact toolchain/container digest for each comparison to make results reproducible.
- [ ] **M15-016** — Feed confirmed INV-09 bugs into permanent regression tests and M48 traceability evidence.
- [ ] **M15-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M15-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M15-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M15-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M15-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M15-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M15-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M15-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M15-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M15-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M15-027** — Inject a known validator bug and prove the harness flags the discrepancy.
- [ ] **M15-028** — Exercise feature-configuration mismatches and verify they are classified, not falsely reported as validator errors.
- [ ] **M15-029** — Reproduce results from a clean environment using only pinned artifacts.
- [ ] **M15-030** — Track disagreement rate and unresolved severity over time.
- [ ] **M15-031** — Require reviewed disposition for every release-blocking disagreement before production promotion.
- [ ] **M15-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M15-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M15-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M15-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M15-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M15-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M15-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M15-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M15-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M15-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M15-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M15-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M15-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M15-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M15-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M15-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M15-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M15-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M15-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M15-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M15-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M15: 52 items.**

## M16 — Determinism specification [P1]

**Objective:** Define normative execution semantics required for the deterministic profile, including numeric edge cases and all host-observable nondeterminism.
**Primary dependencies/interfaces:** M05, M17, M18, M20, M21
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M16-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Determinism specification**; record escalation paths in M50.
- [ ] **M16-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M16-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M16-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M16-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M16-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M16-007** — Define the exact scope of “same module and inputs”: module bytes, profile revision, imports, initial memories/tables/globals, host resources, architecture, runtime flags, and observable outputs.
- [ ] **M16-008** — Specify integer semantics, traps, overflow behavior, shifts, conversions, and any implementation latitude that must be normalized.
- [ ] **M16-009** — Specify floating-point requirements including NaN payload/canonicalization policy, signed zero, rounding mode assumptions, fused operations, subnormal handling, and architecture-dependent behavior.
- [ ] **M16-010** — Define SIMD and relaxed-SIMD policy explicitly; disable constructs that cannot meet the stated equivalence class.
- [ ] **M16-011** — Define threads/atomics policy including scheduling nondeterminism, memory-model observables, wait/notify, and whether deterministic profiles prohibit shared-memory concurrency.
- [ ] **M16-012** — Define deterministic handling or prohibition of clocks, randomness, filesystem metadata/order, networking, environment, process state, device state, and external services.
- [ ] **M16-013** — Specify host-call ordering, replayability, idempotence expectations, and permitted side effects.
- [ ] **M16-014** — Define trap/resource-exhaustion semantics and whether resource-limit differences across hosts are considered deterministic failure equivalence.
- [ ] **M16-015** — Define byte-for-byte versus normalized-equivalence outputs for text, floating values, maps/sets, timestamps, and error representations.
- [ ] **M16-016** — Version the determinism contract and bind its revision into profiles and validation attestations.
- [ ] **M16-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M16-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M16-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M16-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M16-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M16-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M16-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M16-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M16-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M16-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M16-027** — Build a determinism corpus covering numeric corner cases, NaNs, SIMD, branches, memory growth, host imports, and resource limits.
- [ ] **M16-028** — Run repeated executions on identical hosts to detect scheduling/runtime nondeterminism.
- [ ] **M16-029** — Run M20 cross-architecture comparisons and classify every non-identical output against the normative equivalence rules.
- [ ] **M16-030** — Test that prohibited nondeterministic features are rejected at validation/admission rather than merely documented.
- [ ] **M16-031** — Require architecture/runtime owner sign-off on every proposed change to determinism semantics.
- [ ] **M16-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M16-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M16-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M16-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M16-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M16-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M16-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M16-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M16-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M16-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M16-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M16-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M16-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M16-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M16-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M16-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M16-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M16-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M16-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M16-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M16-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M16: 52 items.**

## M17 — Host-import capability contract [P1]

**Objective:** Replace ambient authority with explicitly typed, scoped, policy-governed host capabilities available to admitted modules.
**Primary dependencies/interfaces:** M10, M16, M18, M23, M24
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M17-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Host-import capability contract**; record escalation paths in M50.
- [ ] **M17-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M17-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M17-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M17-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M17-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M17-007** — Define a versioned import namespace and typed signature for every permitted host function/resource.
- [ ] **M17-008** — Require explicit capability grants at instantiation; absence of a grant must deny the import even if the runtime can provide it.
- [ ] **M17-009** — Model capability scope such as filesystem subtree, network destination, clock class, secret identifier, device, or service action.
- [ ] **M17-010** — Prohibit wildcard/ambient process environment inheritance unless a separately governed profile explicitly allows it.
- [ ] **M17-011** — Bind import contract version and granted capability set to admission evidence and runtime instance identity.
- [ ] **M17-012** — Validate import names, module namespaces, function signatures, resource handles, and ownership/lifetime rules before instantiation.
- [ ] **M17-013** — Define revocation and lease/expiry semantics for long-lived resources.
- [ ] **M17-014** — Ensure handles are unforgeable/non-confusable across tenants and cannot be converted into broader ambient OS authority.
- [ ] **M17-015** — Define deterministic-profile behavior for imports with nondeterministic outputs or side effects.
- [ ] **M17-016** — Audit all import calls at an assurance-appropriate level while redacting secrets and high-cardinality payloads.
- [ ] **M17-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M17-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M17-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M17-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M17-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M17-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M17-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M17-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M17-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M17-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M17-027** — Attempt undeclared imports, wrong signatures, wrong namespaces, stale/revoked handles, and cross-tenant handle reuse.
- [ ] **M17-028** — Test scope enforcement with path traversal, DNS rebinding/redirect, symlink, wildcard, and equivalent capability-escape cases where relevant.
- [ ] **M17-029** — Verify deterministic profiles reject or normalize nondeterministic host functions per M16.
- [ ] **M17-030** — Contract-test import ABI across every certified runtime engine.
- [ ] **M17-031** — Fuzz import boundary serialization/deserialization and resource-handle lifetime transitions.
- [ ] **M17-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M17-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M17-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M17-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M17-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M17-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M17-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M17-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M17-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M17-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M17-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M17-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M17-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M17-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M17-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M17-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M17-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M17-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M17-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M17-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M17-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M17: 52 items.**

## M18 — WASI policy adapter [P1]

**Objective:** Map WASI interfaces to explicit deny-by-default capability policy while preserving version and preview semantics.
**Primary dependencies/interfaces:** M05, M16, M17, M23, M24
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M18-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **WASI policy adapter**; record escalation paths in M50.
- [ ] **M18-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M18-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M18-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M18-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M18-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M18-007** — Pin supported WASI interface sets/revisions and map each interface/function to M17 capability identifiers.
- [ ] **M18-008** — Default-deny filesystem, sockets/network, clocks, random, environment, arguments, process/control, device, and other host access.
- [ ] **M18-009** — Define preopen/path policy with normalized path handling, symlink/reparse behavior, read/write/create/delete rights, and directory traversal prevention.
- [ ] **M18-010** — Define network policy by protocol/address/port/DNS semantics and make redirection/rebinding behavior explicit.
- [ ] **M18-011** — Classify clocks and randomness as deterministic, virtualized, recorded/replayed, or prohibited under each profile.
- [ ] **M18-012** — Sanitize environment variables/arguments and prevent leakage of host secrets or deployment internals.
- [ ] **M18-013** — Constrain resource counts, descriptor counts, sockets, outstanding operations, and host-buffer sizes.
- [ ] **M18-014** — Map WASI errors to stable M12 codes without exposing host-sensitive details.
- [ ] **M18-015** — Support per-tenant capability templates with signed/versioned configuration and rollback.
- [ ] **M18-016** — Record exact WASI policy revision in M08 and runtime compatibility certification.
- [ ] **M18-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M18-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M18-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M18-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M18-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M18-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M18-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M18-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M18-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M18-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M18-027** — Run deny-by-default tests with no grants and verify every privileged interface is inaccessible.
- [ ] **M18-028** — Test path traversal, symlink/junction escape, absolute paths, encoding edge cases, and race-sensitive filesystem operations.
- [ ] **M18-029** — Test network egress restrictions including DNS changes, redirects, IPv4/IPv6 forms, and prohibited ports.
- [ ] **M18-030** — Verify clocks/random/environment behavior against M16 determinism rules.
- [ ] **M18-031** — Run WASI conformance fixtures across every supported runtime version.
- [ ] **M18-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M18-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M18-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M18-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M18-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M18-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M18-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M18-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M18-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M18-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M18-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M18-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M18-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M18-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M18-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M18-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M18-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M18-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M18-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M18-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M18-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M18: 52 items.**

## M19 — Component Model / WIT validator [P1]

**Objective:** Validate WebAssembly Component Model binaries and WIT interface contracts when component-model execution is in scope.
**Primary dependencies/interfaces:** M05, M17, M18, M21
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M19-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Component Model / WIT validator**; record escalation paths in M50.
- [ ] **M19-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M19-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M19-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M19-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M19-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M19-007** — Define whether component-model support is in scope; if not, explicitly reject component binaries with a stable unsupported-feature code.
- [ ] **M19-008** — Pin Component Model and WIT revisions in M05 rather than accepting floating toolchain defaults.
- [ ] **M19-009** — Parse and validate component sections, nested core modules/components, aliases, instances, imports/exports, types, resources, and canonical functions.
- [ ] **M19-010** — Validate WIT worlds/interfaces/types including naming rules, version/package identity, type recursion/size constraints, and interface compatibility.
- [ ] **M19-011** — Validate canonical ABI lift/lower options, encodings, realloc/post-return functions, memory selection, and resource ownership/borrowing rules.
- [ ] **M19-012** — Derive component-model feature usage from bytes and interface constructs for profile enforcement.
- [ ] **M19-013** — Propagate capability requirements from WIT imports into M17/M18 policy checks.
- [ ] **M19-014** — Bound nested component/module depth and aggregate encoded/decoded complexity through M13.
- [ ] **M19-015** — Bind adapters/shims to provenance and compatibility evidence rather than trusting dynamically supplied adapter code.
- [ ] **M19-016** — Return stable error location/context spanning component, nested module, WIT package, interface, and canonical ABI operation.
- [ ] **M19-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M19-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M19-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M19-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M19-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M19-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M19-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M19-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M19-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M19-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M19-027** — Use official/spec-derived Component Model and WIT positive/negative fixtures for the pinned revision.
- [ ] **M19-028** — Test ownership/borrow/resource-lifetime violations and canonical ABI misconfiguration.
- [ ] **M19-029** — Fuzz nested components and WIT parsing with depth/size governors enabled.
- [ ] **M19-030** — Cross-validate component acceptance against independent compatible toolchains/runtimes.
- [ ] **M19-031** — Test explicit rejection path when component-model support is disabled by profile or engine.
- [ ] **M19-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M19-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M19-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M19-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M19-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M19-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M19-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M19-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M19-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M19-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M19-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M19-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M19-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M19-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M19-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M19-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M19-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M19-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M19-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M19-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M19-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M19: 52 items.**

## M20 — Cross-architecture determinism certification [P1]

**Objective:** Demonstrate deterministic-profile behavior across every supported CPU architecture and runtime target combination.
**Primary dependencies/interfaces:** M16, M21, M29, M31
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M20-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Cross-architecture determinism certification**; record escalation paths in M50.
- [ ] **M20-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M20-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M20-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M20-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M20-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M20-007** — Define the certified architecture matrix, including microarchitecture/runtime flags that can alter numeric or code-generation behavior.
- [ ] **M20-008** — Build a versioned corpus spanning integer, floating-point, SIMD, memory, control flow, traps, imports, and resource-boundary behaviors.
- [ ] **M20-009** — Execute identical module/input vectors with identical profile/import fixtures on each target using controlled environment configuration.
- [ ] **M20-010** — Capture output, state digest, trap/error class, and execution metadata in canonical form.
- [ ] **M20-011** — Normalize only outputs explicitly permitted by M16; never hide unexplained divergence with broad tolerances.
- [ ] **M20-012** — Record runtime engine build, compiler backend, CPU features, OS/kernel, and relevant flags for every result.
- [ ] **M20-013** — Investigate and classify divergence as spec-permitted, deterministic-profile defect, runtime defect, or environment/configuration error.
- [ ] **M20-014** — Create architecture-specific deny rules when a feature cannot currently meet the deterministic contract.
- [ ] **M20-015** — Re-run certification whenever engine, compiler, CPU feature policy, OS ABI, or determinism profile changes.
- [ ] **M20-016** — Publish signed certification artifacts consumed by M21 and production exit gating.
- [ ] **M20-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M20-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M20-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M20-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M20-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M20-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M20-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M20-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M20-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M20-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M20-027** — Include adversarial NaN/subnormal/conversion/SIMD cases known to expose architecture differences.
- [ ] **M20-028** — Run repeated trials per architecture to separate intra-host nondeterminism from cross-host divergence.
- [ ] **M20-029** — Inject a deliberate architecture-specific behavior difference and prove certification fails.
- [ ] **M20-030** — Verify unsupported matrix cells cannot be selected for production admission.
- [ ] **M20-031** — Retain raw result artifacts sufficient to independently reproduce every certification verdict.
- [ ] **M20-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M20-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M20-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M20-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M20-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M20-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M20-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M20-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M20-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M20-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M20-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M20-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M20-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M20-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M20-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M20-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M20-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M20-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M20-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M20-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M20-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M20: 52 items.**

## M21 — Runtime/validator compatibility matrix [P1]

**Objective:** Maintain an authoritative certification matrix across validator, spec/proposal set, runtime engine/build, architecture, OS/host ABI, and profile.
**Primary dependencies/interfaces:** M05, M06, M20, M24, M41
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M21-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Runtime/validator compatibility matrix**; record escalation paths in M50.
- [ ] **M21-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M21-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M21-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M21-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M21-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M21-007** — Define a machine-readable matrix schema with exact immutable identities for validator build, registry revisions, engine build, CPU architecture, OS ABI, profile, and certification status.
- [ ] **M21-008** — Distinguish tested/supported, tested/unsupported, untested, revoked, and end-of-life states.
- [ ] **M21-009** — Link every supported matrix cell to concrete conformance, determinism, performance, and security evidence.
- [ ] **M21-010** — Require explicit recertification after any dimension changes; prohibit wildcard claims such as “all patch releases” without a governed compatibility rule.
- [ ] **M21-011** — Integrate engine capability facts from M06 and determinism evidence from M20.
- [ ] **M21-012** — Represent architecture-specific runtime flags and host dependencies that materially affect semantics.
- [ ] **M21-013** — Sign released matrices and activate atomically through M43.
- [ ] **M21-014** — Expose matrix revision in health, logs, attestations, and admission decisions.
- [ ] **M21-015** — Implement selection logic that rejects any execution request outside an actively supported matrix cell.
- [ ] **M21-016** — Connect EOL/revocation state to M41 so vulnerable cells can be disabled immediately.
- [ ] **M21-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M21-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M21-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M21-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M21-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M21-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M21-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M21-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M21-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M21-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M21-027** — Generate pairwise and boundary tests across every active matrix dimension.
- [ ] **M21-028** — Attempt admission using an untested/revoked/EOL cell and require deterministic denial.
- [ ] **M21-029** — Verify matrix regeneration detects orphaned engine/profile/spec entries.
- [ ] **M21-030** — Reproduce sampled certification cells from clean infrastructure using linked evidence.
- [ ] **M21-031** — Test atomic matrix rollback and verify no request observes a mixed revision.
- [ ] **M21-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M21-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M21-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M21-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M21-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M21-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M21-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M21-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M21-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M21-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M21-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M21-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M21-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M21-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M21-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M21-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M21-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M21-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M21-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M21-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M21-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M21: 52 items.**

## M22 — Profile schema and signed distribution [P1]

**Objective:** Define and securely distribute the versioned PK_ISA_PROFILE/1 policy that controls allowed features, determinism class, and limits.
**Primary dependencies/interfaces:** M05, M06, M13, M16, M23, M42, M43
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M22-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Profile schema and signed distribution**; record escalation paths in M50.
- [ ] **M22-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M22-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M22-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M22-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M22-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M22-007** — Formalize PK_ISA_PROFILE/1 in a strict machine-readable schema with profile ID, revision, allowed/denied features, determinism class, limits, engine constraints, validity window, and metadata.
- [ ] **M22-008** — Define canonical serialization and cryptographic signing for profile artifacts.
- [ ] **M22-009** — Validate referential integrity against M05 feature IDs, M06 engine constraints, and M13 limit dimensions before activation.
- [ ] **M22-010** — Define monotonic revision/history semantics; never mutate a published profile revision in place.
- [ ] **M22-011** — Define activation, staged rollout, rollback, emergency disable, and supersession semantics.
- [ ] **M22-012** — Enforce issuer authorization and multi-party approval for production profile changes where required by risk level.
- [ ] **M22-013** — Prevent downgrade to superseded/vulnerable profiles through minimum-revision policy and M23 authorization.
- [ ] **M22-014** — Distribute profiles over authenticated channels and verify signature/digest at every consumer before use.
- [ ] **M22-015** — Persist full provenance and prior revisions in M42.
- [ ] **M22-016** — Expose active profile IDs/revisions in M08, M33, M35, M37, and M38.
- [ ] **M22-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M22-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M22-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M22-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M22-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M22-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M22-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M22-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M22-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M22-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M22-027** — Schema-test valid/invalid profiles including unknown feature IDs, contradictory constraints, bad limits, and invalid validity windows.
- [ ] **M22-028** — Tamper profile bytes/signature and require rejection.
- [ ] **M22-029** — Test downgrade, rollback, and emergency-disable flows with concurrent validation requests.
- [ ] **M22-030** — Verify consumers never use a partially downloaded or half-activated profile set.
- [ ] **M22-031** — Reproduce profile history and signature chain from the provenance store.
- [ ] **M22-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M22-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M22-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M22-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M22-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M22-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M22-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M22-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M22-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M22-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M22-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M22-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M22-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M22-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M22-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M22-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M22-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M22-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M22-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M22-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M22-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M22: 52 items.**

## M23 — Policy-engine integration contract [P1]

**Objective:** Connect external policy decisions to profile selection and execution authorization through an authenticated, downgrade-resistant contract.
**Primary dependencies/interfaces:** M10, M22, M27, M42, M43
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M23-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Policy-engine integration contract**; record escalation paths in M50.
- [ ] **M23-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M23-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M23-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M23-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M23-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M23-007** — Define request/response schemas between GAP-13 policy engine and INV-09 including subject, tenant, workload, artifact digest, requested operation, candidate profile, and contextual claims.
- [ ] **M23-008** — Authenticate both services and authorize the policy engine identity allowed to issue production profile decisions.
- [ ] **M23-009** — Bind each policy decision to artifact digest, tenant/workload, profile revision, policy bundle revision, decision ID, and expiry/freshness.
- [ ] **M23-010** — Verify policy response signatures/MACs or use a mutually authenticated trusted channel with non-repudiable audit IDs according to threat model.
- [ ] **M23-011** — Fail closed on policy timeout, malformed response, unknown profile, stale decision, or mismatched request context.
- [ ] **M23-012** — Prevent profile downgrade by enforcing local minimum-security constraints independent of external policy.
- [ ] **M23-013** — Define cache semantics for policy decisions and all invalidation inputs.
- [ ] **M23-014** — Emit linked M27 audit events for policy request, response, selected profile, and final admission result.
- [ ] **M23-015** — Support staged policy rollout and rollback without allowing mixed bundle/profile revisions in one decision.
- [ ] **M23-016** — Document break-glass behavior; any emergency override must be explicit, time-bounded, separately authorized, and auditable, with a preference for no validation bypass.
- [ ] **M23-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M23-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M23-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M23-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M23-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M23-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M23-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M23-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M23-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M23-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M23-027** — Replay a valid policy decision against a different module/tenant/profile and require rejection.
- [ ] **M23-028** — Simulate policy-engine unavailability, timeout, malformed output, and stale cache and confirm fail-closed behavior.
- [ ] **M23-029** — Test attempted downgrade below locally enforced minimums.
- [ ] **M23-030** — Contract-test schema evolution and unknown optional fields.
- [ ] **M23-031** — Correlate policy decision IDs through logs, traces, attestations, and final runtime admission.
- [ ] **M23-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M23-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M23-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M23-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M23-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M23-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M23-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M23-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M23-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M23-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M23-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M23-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M23-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M23-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M23-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M23-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M23-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M23-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M23-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M23-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M23-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M23: 52 items.**

## M24 — Runtime-hardening handoff contract [P1]

**Objective:** Define the enforceable boundary between INV-09 validation and the runtime sandbox/hardening controls owned by INV-44.
**Primary dependencies/interfaces:** M06, M10, M17, M21, M41
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M24-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Runtime-hardening handoff contract**; record escalation paths in M50.
- [ ] **M24-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M24-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M24-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M24-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M24-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M24-007** — Enumerate which security properties INV-09 guarantees and which are delegated to the runtime: sandboxing, memory isolation, CFI, JIT/AOT policy, executable memory, syscall/container isolation, and patch posture.
- [ ] **M24-008** — Define a versioned handoff object containing admitted module digest, detected features, profile, engine identity, import grants, limits, and attestation reference.
- [ ] **M24-009** — Require the runtime to prove its active hardening configuration matches the certified M06/M21 entry before accepting the handoff.
- [ ] **M24-010** — Specify W^X/executable-memory expectations and approved JIT/AOT modes per platform.
- [ ] **M24-011** — Define memory/table/resource ceilings that must be re-enforced by runtime even if module declarations passed validation.
- [ ] **M24-012** — Define crash/trap containment and tenant isolation responsibilities.
- [ ] **M24-013** — Require engine security patch/CVE state to be checked at admission or deployment activation.
- [ ] **M24-014** — Define telemetry returned from runtime startup so INV-09 can correlate actual engine/configuration with the admitted claim.
- [ ] **M24-015** — Prohibit runtime feature auto-enablement beyond the validated profile.
- [ ] **M24-016** — Define ownership/escalation when a vulnerability spans parser, engine, sandbox, or host capability layers.
- [ ] **M24-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M24-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M24-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M24-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M24-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M24-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M24-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M24-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M24-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M24-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M24-027** — Attempt to start an admitted module under a mismatched or weakened runtime configuration and require refusal.
- [ ] **M24-028** — Test JIT/AOT mode, W^X, memory limits, sandbox state, and feature flags through runtime introspection/integration tests.
- [ ] **M24-029** — Inject stale/vulnerable engine registry state and verify M41 revocation blocks new workloads.
- [ ] **M24-030** — Test runtime crash and trap isolation across tenants.
- [ ] **M24-031** — Audit all runtime entry paths for handoff enforcement parity.
- [ ] **M24-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M24-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M24-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M24-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M24-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M24-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M24-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M24-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M24-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M24-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M24-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M24-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M24-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M24-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M24-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M24-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M24-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M24-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M24-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M24-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M24-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M24: 52 items.**

## M25 — Artifact provenance integration [P1]

**Objective:** Verify artifact signatures, SBOM/provenance evidence, and supply-chain identity before validation and bind that provenance to the verdict.
**Primary dependencies/interfaces:** M04, M07, M08, M10, M46, M47
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M25-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Artifact provenance integration**; record escalation paths in M50.
- [ ] **M25-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M25-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M25-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M25-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M25-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M25-007** — Define accepted provenance formats/trust policies and exact evidence required for production artifacts.
- [ ] **M25-008** — Verify artifact signature before executing or trusting associated metadata; bind verification to M07 digest.
- [ ] **M25-009** — Validate issuer identity, trust root, namespace/repository, build workflow identity, source revision, and freshness according to policy.
- [ ] **M25-010** — Reject provenance whose subject digest does not exactly match the Wasm module bytes being validated.
- [ ] **M25-011** — Verify SBOM identity/digest linkage when SBOM is required; treat missing or mismatched SBOM as policy failure, not warning, for governed profiles.
- [ ] **M25-012** — Record provenance statement digest, signer/issuer, verification result, and policy revision in M08.
- [ ] **M25-013** — Define handling for multiple attestations/signatures and conflicting provenance claims.
- [ ] **M25-014** — Integrate revocation/compromise lists for signing identities and build systems.
- [ ] **M25-015** — Keep provenance verification network dependencies out of the critical path where possible through signed trust snapshots/cached transparency proofs with safe freshness rules.
- [ ] **M25-016** — Expose provenance failure reasons through M12/M37 without leaking secrets or internal repository metadata beyond authorization.
- [ ] **M25-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M25-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M25-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M25-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M25-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M25-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M25-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M25-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M25-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M25-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M25-027** — Test unsigned, bad-signature, untrusted-issuer, wrong-subject-digest, wrong-repository/workflow, expired/revoked, and missing-SBOM cases.
- [ ] **M25-028** — Replay valid provenance against a different but similarly named artifact and require rejection.
- [ ] **M25-029** — Test offline verification using pinned trust material and verify stale-trust behavior is fail-closed according to policy.
- [ ] **M25-030** — Verify provenance evidence survives cache hits and remains bound to cached validation results.
- [ ] **M25-031** — Run end-to-end supply-chain fixture from reproducible build metadata through admission.
- [ ] **M25-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M25-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M25-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M25-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M25-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M25-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M25-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M25-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M25-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M25-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M25-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M25-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M25-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M25-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M25-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M25-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M25-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M25-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M25-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M25-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M25-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M25: 52 items.**

## M26 — Tenant isolation model for validation service [P1]

**Objective:** Prevent one tenant from exhausting, observing, or influencing another tenant through validator resources, caches, diagnostics, or control state.
**Primary dependencies/interfaces:** M09, M13, M27, M34, M35
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M26-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Tenant isolation model for validation service**; record escalation paths in M50.
- [ ] **M26-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M26-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M26-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M26-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M26-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M26-007** — Define tenant identity/authentication source and propagate an immutable tenant ID through request, cache, metrics policy, logs, traces, and audit.
- [ ] **M26-008** — Enforce per-tenant request rate, concurrency, CPU/work budget, memory, upload bytes, and cache quota.
- [ ] **M26-009** — Use fair scheduling so a high-volume tenant cannot starve other tenants within shared service capacity.
- [ ] **M26-010** — Namespace tenant-sensitive cache entries and prevent cross-tenant discovery through error text, cache hit timing, IDs, or metrics labels.
- [ ] **M26-011** — Define which parsed/validation artifacts are safe to deduplicate globally by public content digest and which metadata must remain tenant-scoped.
- [ ] **M26-012** — Isolate temporary files, memory buffers, worker processes/threads, and crash dumps according to threat model.
- [ ] **M26-013** — Redact tenant data from shared observability systems and enforce access controls on logs/traces/audit records.
- [ ] **M26-014** — Define noisy-neighbor saturation behavior and backpressure; reject predictably rather than causing global OOM or latency collapse.
- [ ] **M26-015** — Ensure profile/policy selection cannot be influenced across tenant namespaces.
- [ ] **M26-016** — Document data retention/deletion expectations for tenant-associated validation evidence.
- [ ] **M26-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M26-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M26-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M26-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M26-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M26-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M26-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M26-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M26-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M26-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M26-027** — Run concurrent adversarial workloads from multiple tenant identities and verify quotas/fairness.
- [ ] **M26-028** — Probe cache timing and diagnostic responses for cross-tenant information leakage.
- [ ] **M26-029** — Force worker crash/OOM for one tenant and verify other tenants remain isolated.
- [ ] **M26-030** — Test authentication confusion, tenant-ID spoofing, and privilege escalation through forwarded headers/claims.
- [ ] **M26-031** — Verify observability access control and redaction with representative sensitive metadata.
- [ ] **M26-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M26-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M26-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M26-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M26-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M26-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M26-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M26-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M26-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M26-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M26-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M26-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M26-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M26-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M26-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M26-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M26-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M26-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M26-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M26-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M26-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M26: 52 items.**

## M27 — Security audit event stream [P1]

**Objective:** Create tamper-evident, queryable security events for validation, policy, configuration, bypass, and admission actions.
**Primary dependencies/interfaces:** M08, M10, M22, M23, M35, M42
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M27-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Security audit event stream**; record escalation paths in M50.
- [ ] **M27-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M27-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M27-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M27-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M27-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M27-007** — Define a versioned event schema with event ID, timestamp/sequence, actor/service identity, tenant/workload, module digest, action, outcome, rule/profile/policy revisions, and correlation IDs.
- [ ] **M27-008** — Emit events for profile/spec/engine/config changes, validation accepts/rejects, parser failures, provenance failures, policy decisions, admission allows/denies, bypass attempts, revocations, and emergency operations.
- [ ] **M27-009** — Use append-only/tamper-evident storage or cryptographic chaining where assurance requirements demand it.
- [ ] **M27-010** — Authenticate event producers and prevent tenant-controlled fields from masquerading as trusted actor metadata.
- [ ] **M27-011** — Define bounded event payloads and strict redaction of secrets, raw module bytes, credentials, and sensitive host data.
- [ ] **M27-012** — Guarantee stable event IDs/idempotency semantics so retries do not create ambiguous duplicate security actions.
- [ ] **M27-013** — Define delivery failure behavior and buffering; security-critical admission must not silently lose required audit evidence.
- [ ] **M27-014** — Time-sync or sequence events so causal ordering can be reconstructed even during clock skew.
- [ ] **M27-015** — Set retention, access control, export, legal/compliance, and destruction rules.
- [ ] **M27-016** — Link attestation, policy decision, trace, configuration revision, and runtime admission event IDs end to end.
- [ ] **M27-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M27-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M27-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M27-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M27-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M27-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M27-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M27-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M27-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M27-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M27-027** — Verify every defined security-sensitive action produces exactly the required event schema.
- [ ] **M27-028** — Tamper/delete/reorder events in a test ledger and verify integrity controls detect the manipulation.
- [ ] **M27-029** — Test event sink outage/backpressure and confirm documented fail-closed or durable-buffer behavior.
- [ ] **M27-030** — Fuzz attacker-controlled strings and ensure no log/event injection or unbounded payload occurs.
- [ ] **M27-031** — Reconstruct a full incident timeline from only retained audit records and linked immutable evidence.
- [ ] **M27-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M27-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M27-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M27-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M27-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M27-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M27-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M27-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M27-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M27-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M27-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M27-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M27-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M27-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M27-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M27-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M27-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M27-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M27-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M27-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M27-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M27: 52 items.**

## M28 — Side-channel threat assessment [P1]

**Objective:** Identify and mitigate information leakage through timing, caches, resource contention, compilation metadata, feature probing, and multi-tenant shared state.
**Primary dependencies/interfaces:** M09, M24, M26, M29, M34
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M28-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Side-channel threat assessment**; record escalation paths in M50.
- [ ] **M28-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M28-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M28-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M28-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M28-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M28-007** — Create an explicit side-channel threat model covering local co-tenant attackers, remote tenants, malicious modules, compromised clients, and privileged operators as applicable.
- [ ] **M28-008** — Inventory shared resources: validation cache, CPU caches, worker pools, branch predictors, filesystem/object caches, JIT/AOT caches, metrics, error paths, and timing-visible policy dependencies.
- [ ] **M28-009** — Classify which secrets could be inferred: tenant artifact existence, feature/profile usage, module size/structure, capability grants, other-tenant activity, and host/runtime configuration.
- [ ] **M28-010** — Measure timing distributions for cache hit/miss, accepted/rejected modules, early/late parse errors, signature verification, and policy decisions.
- [ ] **M28-011** — Reduce unnecessarily data-dependent timing for sensitive comparisons and avoid secret-derived cache keys/labels.
- [ ] **M28-012** — Partition or blind caches where cross-tenant artifact-existence disclosure is unacceptable.
- [ ] **M28-013** — Control compilation/JIT metadata sharing and temporary artifacts across tenants.
- [ ] **M28-014** — Evaluate speculative-execution/microarchitectural exposure delegated to runtime/host and document compensating isolation controls.
- [ ] **M28-015** — Define acceptable residual leakage and require security-owner approval for non-mitigated channels.
- [ ] **M28-016** — Repeat assessment when cache architecture, runtime, host isolation, or tenancy model changes.
- [ ] **M28-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M28-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M28-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M28-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M28-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M28-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M28-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M28-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M28-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M28-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M28-027** — Run statistical timing tests for cross-tenant cache-existence probing with controlled noise.
- [ ] **M28-028** — Attempt to infer other-tenant load via validation latency and worker saturation.
- [ ] **M28-029** — Test error-path timing for feature/policy/provenance oracle behavior.
- [ ] **M28-030** — Verify cache partitioning/blinding configuration in production-like deployment.
- [ ] **M28-031** — Track every accepted residual side channel in M51 with scope and expiration where remediation is deferred.
- [ ] **M28-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M28-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M28-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M28-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M28-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M28-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M28-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M28-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M28-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M28-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M28-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M28-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M28-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M28-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M28-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M28-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M28-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M28-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M28-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M28-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M28-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M28: 52 items.**

## M29 — Benchmark harness [P2]

**Objective:** Measure reproducible validation latency, throughput, resource usage, and power/thermal characteristics across realistic and adversarial modules.
**Primary dependencies/interfaces:** M13, M30, M31, M34
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M29-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Benchmark harness**; record escalation paths in M50.
- [ ] **M29-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M29-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M29-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M29-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M29-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M29-007** — Define benchmark classes by module size, function/type count, section composition, feature mix, validity, cache state, and adversarial complexity.
- [ ] **M29-008** — Include tiny, median ecosystem, near-4-MiB, maximum-policy, and parser/type-check worst-case fixtures.
- [ ] **M29-009** — Measure p50/p95/p99/max latency, throughput, CPU time, wall time, peak RSS, allocation count/bytes, I/O, and cache behavior.
- [ ] **M29-010** — Measure cold-start, warm process, cold cache, hot cache, and concurrent load separately.
- [ ] **M29-011** — Capture host hardware, CPU governor, core count/affinity, memory, OS/kernel, Python/native runtime, validator build, and configuration revision.
- [ ] **M29-012** — Use sufficient warmup/sample sizes and report confidence/variance rather than single-run numbers.
- [ ] **M29-013** — Prevent benchmark corpus drift by content-addressing all fixtures and storing generation recipes.
- [ ] **M29-014** — Record power/thermal data on representative edge targets when this requirement is material to deployment.
- [ ] **M29-015** — Export machine-readable results suitable for M30 automated regression gates.
- [ ] **M29-016** — Separate parser, type validation, feature detection, provenance verification, attestation, and end-to-end measurements.
- [ ] **M29-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M29-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M29-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M29-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M29-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M29-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M29-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M29-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M29-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M29-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M29-027** — Re-run the same benchmark commit/configuration and verify variance is within documented tolerance.
- [ ] **M29-028** — Validate harness overhead by measuring no-op/baseline paths.
- [ ] **M29-029** — Use adversarial fixtures that maximize nesting, type work, vectors, and rejection depth under legal limits.
- [ ] **M29-030** — Compare at least one release against the previous production baseline on identical hardware.
- [ ] **M29-031** — Archive raw samples and environment metadata so aggregate percentiles can be independently recomputed.
- [ ] **M29-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M29-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M29-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M29-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M29-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M29-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M29-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M29-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M29-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M29-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M29-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M29-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M29-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M29-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M29-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M29-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M29-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M29-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M29-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M29-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M29-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M29: 52 items.**

## M30 — Release performance gate [P2]

**Objective:** Automatically block releases that regress validated performance or exceed approved resource/SLO limits.
**Primary dependencies/interfaces:** M29, M39, M52
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M30-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Release performance gate**; record escalation paths in M50.
- [ ] **M30-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M30-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M30-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M30-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M30-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M30-007** — Define machine-readable thresholds for latency percentiles, throughput, peak memory, allocations, CPU, and adversarial worst-case behavior by benchmark class.
- [ ] **M30-008** — Express thresholds relative to both absolute SLOs and an approved baseline to detect regressions below the SLO ceiling.
- [ ] **M30-009** — Specify statistically meaningful regression rules and minimum sample counts to avoid noisy pass/fail decisions.
- [ ] **M30-010** — Run on controlled benchmark agents or normalize hardware sufficiently to make comparisons actionable.
- [ ] **M30-011** — Gate separately on cold/warm and cache-hit/cache-miss paths where operationally relevant.
- [ ] **M30-012** — Treat timeout/OOM/crash as hard failure independent of percentile aggregation.
- [ ] **M30-013** — Prevent threshold editing in the same unreviewed change that causes a regression; require explicit performance-owner approval.
- [ ] **M30-014** — Store gate result, raw result artifact, baseline ID, validator build, and environment metadata as release evidence.
- [ ] **M30-015** — Support exception linkage only through M51 with expiry and compensating controls.
- [ ] **M30-016** — Feed release gate status into M52 production exit evaluation.
- [ ] **M30-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M30-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M30-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M30-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M30-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M30-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M30-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M30-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M30-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M30-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M30-027** — Inject controlled slowdown/memory inflation and prove the gate blocks release.
- [ ] **M30-028** — Validate noise handling with repeated unchanged builds.
- [ ] **M30-029** — Test baseline rollover/approval workflow and ensure historical results remain immutable.
- [ ] **M30-030** — Test missing/corrupt benchmark results and require NO_GO rather than implicit pass.
- [ ] **M30-031** — Verify adversarial-case thresholds are evaluated even when median workloads remain fast.
- [ ] **M30-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M30-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M30-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M30-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M30-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M30-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M30-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M30-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M30-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M30-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M30-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M30-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M30-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M30-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M30-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M30-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M30-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M30-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M30-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M30-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M30-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M30: 52 items.**

## M31 — Soak and fleet-scale test suite [P2]

**Objective:** Prove long-duration stability and fleet behavior under realistic mixed workloads, cache churn, configuration rotation, restarts, and degraded dependencies.
**Primary dependencies/interfaces:** M09, M26, M29, M32, M39
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M31-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Soak and fleet-scale test suite**; record escalation paths in M50.
- [ ] **M31-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M31-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M31-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M31-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M31-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M31-007** — Define sustained workload mixes of valid, invalid, malformed, provenance-failing, cache-hit, cache-miss, multiple-profile, and multiple-tenant requests.
- [ ] **M31-008** — Run long-duration tests sufficient to expose leaks, fragmentation, queue buildup, file-descriptor leaks, cache pathologies, and timer/sequence rollover issues.
- [ ] **M31-009** — Exercise fleet-scale concurrency and shard/worker counts representative of production peak plus safety margin.
- [ ] **M31-010** — Rotate profiles, spec registries, engine registries, signing keys, and configuration revisions during active load.
- [ ] **M31-011** — Restart individual workers, whole instances, and dependent services without losing correctness or serving stale accepts.
- [ ] **M31-012** — Exercise cache churn, eviction, cold restart, and reconstruction paths.
- [ ] **M31-013** — Inject dependency latency/degradation while measuring backpressure, admission behavior, and tenant fairness.
- [ ] **M31-014** — Track memory/CPU/latency/error-rate trends over time, not only end-of-run summaries.
- [ ] **M31-015** — Verify audit/log/metric pipelines sustain event volume without dropping security-critical records.
- [ ] **M31-016** — Archive test topology, workload generator seed, configuration, and raw telemetry for reproducibility.
- [ ] **M31-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M31-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M31-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M31-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M31-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M31-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M31-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M31-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M31-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M31-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M31-027** — Require no unbounded memory/resource growth over the approved soak duration.
- [ ] **M31-028** — Verify configuration rotations are atomic and every request can be attributed to one coherent revision set.
- [ ] **M31-029** — Demonstrate recovery from worker/service restarts without accepting unvalidated modules.
- [ ] **M31-030** — Measure noisy-neighbor isolation under multi-tenant peak load.
- [ ] **M31-031** — Reproduce at least one discovered soak defect from a minimized deterministic scenario and add regression coverage.
- [ ] **M31-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M31-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M31-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M31-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M31-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M31-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M31-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M31-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M31-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M31-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M31-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M31-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M31-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M31-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M31-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M31-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M31-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M31-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M31-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M31-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M31-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M31: 52 items.**

## M32 — Fault-injection suite [P2]

**Objective:** Validate fail-closed behavior and recoverability under corrupted artifacts, partial I/O, OOM, cache/disk failure, dependency outage, stale configuration, crashes, and replay.
**Primary dependencies/interfaces:** M09, M10, M13, M23, M27, M31, M44
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M32-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Fault-injection suite**; record escalation paths in M50.
- [ ] **M32-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M32-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M32-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M32-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M32-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M32-007** — Create deterministic injection points for artifact read/truncation, hash mismatch, parser failure, allocation failure, cache read/write corruption, disk full, and permission errors.
- [ ] **M32-008** — Inject policy/profile/spec/engine registry unavailability, timeout, stale revision, invalid signature, and partial update.
- [ ] **M32-009** — Inject validator process crash/panic/forced termination at each major pipeline stage.
- [ ] **M32-010** — Simulate out-of-memory and resource-governor rejection without destabilizing the test host.
- [ ] **M32-011** — Inject audit/metrics/log sink failure and verify security-critical behavior matches documented policy.
- [ ] **M32-012** — Exercise clock skew/rollback and sequence discontinuity where attestations or freshness depend on time.
- [ ] **M32-013** — Simulate restart after partially written cache/evidence/configuration state and verify atomicity/recovery.
- [ ] **M32-014** — Inject network partitions and duplicate/replayed requests between validator, policy engine, artifact store, and runtime gate.
- [ ] **M32-015** — Define expected outcome for every fault: reject, retry, degrade, reconstruct, quarantine, or terminate.
- [ ] **M32-016** — Ensure fault hooks cannot be enabled unintentionally in production builds or without privileged authorization.
- [ ] **M32-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M32-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M32-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M32-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M32-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M32-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M32-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M32-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M32-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M32-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M32-027** — Run a fault matrix against ACCEPT and REJECT baseline flows and compare observed behavior with the expected-fault contract.
- [ ] **M32-028** — Verify no injected dependency failure converts an indeterminate condition into ACCEPT.
- [ ] **M32-029** — Verify recovery does not reuse corrupt/stale cache entries or partial configuration.
- [ ] **M32-030** — Test repeated crash/restart loops and bounded replay/idempotency.
- [ ] **M32-031** — Promote every production incident class to a reproducible fault-injection regression when technically feasible.
- [ ] **M32-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M32-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M32-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M32-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M32-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M32-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M32-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M32-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M32-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M32-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M32-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M32-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M32-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M32-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M32-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M32-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M32-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M32-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M32-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M32-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M32-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M32: 52 items.**

## M33 — Health/readiness endpoint or contract [P2]

**Objective:** Expose machine-consumable service health/readiness without conflating process liveness with safe ability to validate and admit modules.
**Primary dependencies/interfaces:** M05, M06, M22, M42, M43
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M33-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Health/readiness endpoint or contract**; record escalation paths in M50.
- [ ] **M33-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M33-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M33-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M33-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M33-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M33-007** — Separate liveness from readiness and define exact semantics for each state.
- [ ] **M33-008** — Include validator build/version, active profile set/revision, spec registry revision, engine capability revision, limits revision, trust/key revision, and dependency status.
- [ ] **M33-009** — Report degraded/not-ready when required configuration is unsigned, stale, inconsistent, partially activated, or references unsupported dependencies.
- [ ] **M33-010** — Avoid exposing sensitive tenant information, secrets, trust material, or raw configuration through health responses.
- [ ] **M33-011** — Use bounded response size and stable machine-readable status codes/reasons.
- [ ] **M33-012** — Ensure readiness is computed from the same active immutable configuration snapshot used by requests.
- [ ] **M33-013** — Define startup sequencing: service must not report ready before profiles/registries/trust roots are fully verified and activated.
- [ ] **M33-014** — Define behavior during profile/registry rotation and rollback without readiness flapping or mixed state.
- [ ] **M33-015** — Expose internal dependency latency/error signals to M34/M38 without making health checks expensive.
- [ ] **M33-016** — Document orchestration probe intervals/timeouts and anti-thundering-herd behavior.
- [ ] **M33-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M33-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M33-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M33-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M33-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M33-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M33-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M33-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M33-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M33-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M33-027** — Start with missing/corrupt configuration and verify liveness/readiness states are correct.
- [ ] **M33-028** — Rotate configuration under probe load and assert no response reports a mixed revision.
- [ ] **M33-029** — Fail each required dependency and verify the documented readiness/degraded transition.
- [ ] **M33-030** — Test high-rate health probing cannot materially degrade validation throughput.
- [ ] **M33-031** — Validate response schema compatibility across rolling upgrades.
- [ ] **M33-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M33-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M33-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M33-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M33-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M33-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M33-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M33-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M33-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M33-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M33-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M33-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M33-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M33-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M33-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M33-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M33-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M33-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M33-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M33-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M33-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M33: 52 items.**

## M34 — Metrics implementation [P2]

**Objective:** Expose bounded-cardinality metrics that reveal correctness, latency, capacity, attacks, cache behavior, and feature/profile usage without leaking tenant data.
**Primary dependencies/interfaces:** M09, M13, M26, M29, M38
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M34-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Metrics implementation**; record escalation paths in M50.
- [ ] **M34-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M34-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M34-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M34-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M34-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M34-007** — Define counters for validate accepted/refused/error, parser/type/policy/provenance/admission failure classes, and configuration changes.
- [ ] **M34-008** — Define latency histograms for end-to-end and major stages, segmented only by bounded dimensions such as profile class/size bucket/result class.
- [ ] **M34-009** — Expose parser resource usage, bytes processed, section/function/type buckets, queue depth, worker utilization, concurrency, and saturation.
- [ ] **M34-010** — Expose cache hit/miss/stale/corrupt/eviction and storage occupancy metrics.
- [ ] **M34-011** — Expose feature-frequency metrics only through bounded known feature IDs and privacy review; never label by module digest or arbitrary tenant string.
- [ ] **M34-012** — Define tenant-level observability via secured separate views or aggregated accounting rather than unbounded global labels.
- [ ] **M34-013** — Measure audit/log sink health and dropped-event counters where loss is possible.
- [ ] **M34-014** — Version metric names/semantics and document units, monotonicity, buckets, and cardinality budgets.
- [ ] **M34-015** — Ensure metrics collection itself has bounded allocations and cannot be attacker-amplified by novel input strings.
- [ ] **M34-016** — Tie release SLO dashboards/alerts to the same metric definitions used by benchmark and operational goals.
- [ ] **M34-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M34-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M34-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M34-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M34-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M34-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M34-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M34-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M34-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M34-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M34-027** — Run cardinality tests with millions of unique module names/digests and prove series count remains bounded.
- [ ] **M34-028** — Verify error counters match known injected fault totals.
- [ ] **M34-029** — Load-test metrics instrumentation overhead at peak validation throughput.
- [ ] **M34-030** — Test histogram bucket suitability against real latency distribution and SLO boundaries.
- [ ] **M34-031** — Audit exported labels for tenant/module/secret leakage.
- [ ] **M34-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M34-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M34-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M34-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M34-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M34-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M34-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M34-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M34-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M34-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M34-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M34-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M34-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M34-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M34-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M34-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M34-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M34-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M34-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M34-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M34-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M34: 52 items.**

## M35 — Structured logging [P2]

**Objective:** Emit consistent, safe, correlated operational logs for validation and admission without leaking secrets or allowing attacker-controlled log injection.
**Primary dependencies/interfaces:** M12, M27, M34, M36, M37
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M35-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Structured logging**; record escalation paths in M50.
- [ ] **M35-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M35-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M35-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M35-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M35-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M35-007** — Define a versioned log schema with timestamp, severity, service/build, operation ID, trace ID, module digest, tenant/workload pseudonymous IDs, stage, outcome, error code, and configuration revisions.
- [ ] **M35-008** — Use structured fields rather than interpolated free-form messages for security-relevant values.
- [ ] **M35-009** — Sanitize/control attacker-supplied strings, strip/control characters, cap lengths, and never log raw module bytes.
- [ ] **M35-010** — Redact secrets, tokens, signatures, private keys, environment values, filesystem contents, and confidential tenant metadata.
- [ ] **M35-011** — Define sampling policy that never drops mandatory security audit events but may sample repetitive operational success logs.
- [ ] **M35-012** — Keep module digest full in secured logs if required for evidence; avoid unsafe truncation that creates collisions in investigations.
- [ ] **M35-013** — Log configuration/profile/spec/engine revision consistently on verdict-changing operations.
- [ ] **M35-014** — Separate expected policy refusals from software/internal errors in severity and alert semantics.
- [ ] **M35-015** — Define retention/access-control requirements and immutable export path for incident evidence.
- [ ] **M35-016** — Ensure log emission failure/backpressure cannot deadlock validation or silently bypass required audit behavior.
- [ ] **M35-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M35-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M35-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M35-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M35-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M35-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M35-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M35-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M35-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M35-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M35-027** — Fuzz names/custom-section strings and verify no line/JSON/control-sequence injection.
- [ ] **M35-028** — Run automated secret scanning against representative logs.
- [ ] **M35-029** — Verify one request can be traced across all major stages using operation/trace IDs.
- [ ] **M35-030** — Simulate log backend outage and validate buffering/drop policy and service behavior.
- [ ] **M35-031** — Schema-validate log records in CI and during canary deployment.
- [ ] **M35-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M35-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M35-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M35-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M35-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M35-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M35-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M35-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M35-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M35-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M35-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M35-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M35-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M35-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M35-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M35-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M35-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M35-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M35-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M35-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M35-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M35: 52 items.**

## M36 — Trace propagation [P2]

**Objective:** Correlate artifact retrieval, policy selection, validation, attestation, admission, compilation, and runtime startup through one controlled trace context.
**Primary dependencies/interfaces:** M23, M25, M35, M38
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M36-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Trace propagation**; record escalation paths in M50.
- [ ] **M36-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M36-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M36-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M36-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M36-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M36-007** — Adopt a standard trace context format and define trusted/untrusted boundaries for incoming trace headers.
- [ ] **M36-008** — Create/propagate spans for artifact fetch/hash, provenance verification, policy decision, parse, type validation, feature detection, cache, attestation, admission, compilation, and runtime startup.
- [ ] **M36-009** — Attach bounded attributes such as result class, profile revision, engine identity, size bucket, and failure code; avoid module bytes, secrets, or high-cardinality arbitrary labels.
- [ ] **M36-010** — Regenerate or sanitize trace context from untrusted clients to prevent trace injection/collision attacks.
- [ ] **M36-011** — Propagate correlation IDs into M27 audit and M35 logs while keeping security events independently trustworthy.
- [ ] **M36-012** — Define sampling rules that retain error/security traces at higher rates without creating tenant privacy leakage.
- [ ] **M36-013** — Instrument asynchronous/retry boundaries so parent/child relationships remain meaningful.
- [ ] **M36-014** — Record configuration revision snapshots on relevant spans to diagnose mixed-version issues.
- [ ] **M36-015** — Measure tracing overhead and cap payload/event counts per request.
- [ ] **M36-016** — Document cross-service clock-skew assumptions and rely on causal span relationships where timestamps are unreliable.
- [ ] **M36-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M36-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M36-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M36-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M36-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M36-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M36-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M36-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M36-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M36-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M36-027** — Run end-to-end traces across success, policy reject, malformed module, cache hit, and dependency-failure paths.
- [ ] **M36-028** — Inject malicious incoming trace headers and verify sanitization.
- [ ] **M36-029** — Verify sampled-out traces do not break mandatory audit correlation.
- [ ] **M36-030** — Load-test tracing overhead at peak throughput.
- [ ] **M36-031** — Use a recorded trace to locate stage latency and exact configuration revisions for a synthetic incident.
- [ ] **M36-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M36-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M36-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M36-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M36-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M36-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M36-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M36-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M36-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M36-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M36-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M36-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M36-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M36-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M36-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M36-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M36-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M36-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M36-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M36-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M36-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M36: 52 items.**

## M37 — Explain view [P2]

**Objective:** Provide an operator-readable, evidence-backed reason chain for why a module was accepted or rejected.
**Primary dependencies/interfaces:** M03, M08, M12, M22, M23, M25, M35
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M37-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Explain view**; record escalation paths in M50.
- [ ] **M37-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M37-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M37-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M37-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M37-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M37-007** — Define an explain schema separate from free-form UI text so it can be rendered consistently in CLI/API/UI.
- [ ] **M37-008** — Show module digest, validation result, detected byte-derived features, declared features/capabilities, selected profile, engine capability entry, and relevant provenance identity.
- [ ] **M37-009** — Show the exact refusal rule/error code and trusted byte offset/section/function context when available.
- [ ] **M37-010** — Distinguish facts derived from bytes from declarations, policy decisions, registry facts, and external provenance evidence.
- [ ] **M37-011** — Link evidence IDs/digests rather than embedding mutable external content.
- [ ] **M37-012** — Redact tenant-confidential capability details and security-sensitive internal diagnostics according to caller authorization.
- [ ] **M37-013** — Make explanation deterministic for the same attestation/evidence set; do not recompute against “current” mutable policy when explaining historical results.
- [ ] **M37-014** — Support historical explanations by loading the exact signed profile/spec/engine/policy revisions referenced by the attestation.
- [ ] **M37-015** — Bound explanation size and number of repeated failures.
- [ ] **M37-016** — Expose enough detail for operators to remediate policy/configuration issues without suggesting bypass of validation.
- [ ] **M37-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M37-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M37-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M37-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M37-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M37-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M37-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M37-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M37-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M37-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M37-027** — Golden-test explanations for representative accept/reject classes.
- [ ] **M37-028** — Verify historical explanation remains identical after current policy/profile changes.
- [ ] **M37-029** — Test authorization/redaction boundaries between tenant operator, platform operator, and security investigator roles.
- [ ] **M37-030** — Ensure attacker-controlled strings cannot inject markup/control content into CLI/UI renderers.
- [ ] **M37-031** — Cross-check explain output fields against the signed M08 attestation and M12 error record.
- [ ] **M37-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M37-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M37-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M37-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M37-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M37-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M37-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M37-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M37-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M37-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M37-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M37-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M37-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M37-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M37-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M37-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M37-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M37-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M37-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M37-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M37-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M37: 52 items.**

## M38 — Dashboards and alerts [P2]

**Objective:** Surface operational and security conditions with actionable, low-noise signals that distinguish normal policy refusal from attack, misconfiguration, dependency failure, saturation, and defects.
**Primary dependencies/interfaces:** M27, M29, M34, M35, M36
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M38-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Dashboards and alerts**; record escalation paths in M50.
- [ ] **M38-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M38-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M38-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M38-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M38-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M38-007** — Create service overview dashboards for throughput, accept/refuse/error rate, latency percentiles, saturation, queue depth, memory, cache, and dependency health.
- [ ] **M38-008** — Create security dashboards for malformed-input rates, bypass attempts, provenance failures, signature failures, revoked-profile/engine use, and unusual feature patterns.
- [ ] **M38-009** — Separate expected policy rejection volume from internal validator errors and parser crashes.
- [ ] **M38-010** — Define alert thresholds from SLOs/baselines with persistence windows and multi-signal correlation to reduce flapping.
- [ ] **M38-011** — Alert on missing telemetry/audit streams as well as abnormal values.
- [ ] **M38-012** — Add runbook links, service ownership, severity, and first-response actions to every paging alert.
- [ ] **M38-013** — Use bounded labels and aggregations that preserve tenant privacy.
- [ ] **M38-014** — Correlate deployment/profile/config revision markers with latency/error changes.
- [ ] **M38-015** — Define capacity alerts for CPU, memory, queue, cache storage, and tenant quota pressure before hard saturation.
- [ ] **M38-016** — Periodically review unused/noisy alerts and validate dashboards after schema/metric changes.
- [ ] **M38-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M38-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M38-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M38-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M38-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M38-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M38-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M38-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M38-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M38-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M38-027** — Fire synthetic alerts for each critical condition and confirm routing, deduplication, severity, and runbook link.
- [ ] **M38-028** — Replay representative incident telemetry and verify dashboard differentiation of attack vs defect vs policy change.
- [ ] **M38-029** — Test telemetry pipeline outage produces an explicit blind-spot alert.
- [ ] **M38-030** — Verify deployment/config markers align with observed metrics and traces.
- [ ] **M38-031** — Run quarterly/regular alert game days and record response findings.
- [ ] **M38-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M38-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M38-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M38-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M38-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M38-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M38-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M38-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M38-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M38-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M38-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M38-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M38-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M38-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M38-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M38-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M38-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M38-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M38-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M38-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M38-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M38: 52 items.**

## M39 — Canary/staged rollout controller [P2]

**Objective:** Deploy validator, profile, registry, and policy changes incrementally with compatibility prechecks, measurable abort criteria, and rapid rollback.
**Primary dependencies/interfaces:** M21, M30, M31, M38, M43
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M39-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Canary/staged rollout controller**; record escalation paths in M50.
- [ ] **M39-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M39-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M39-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M39-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M39-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M39-007** — Define rollout units for validator binary, profiles, spec registry, engine registry, policy bundle, and limits; avoid coupling unrelated changes without necessity.
- [ ] **M39-008** — Run pre-deploy schema/signature/compatibility checks and M52 prerequisite verification before any canary activation.
- [ ] **M39-009** — Select canary populations by controlled tenant/workload/region/instance policy without exposing users to unsupported matrix cells.
- [ ] **M39-010** — Define objective abort thresholds for internal errors, unexpected rejects, latency, resource usage, determinism discrepancies, and security events.
- [ ] **M39-011** — Compare canary to control using equivalent traffic/classes and account for workload mix.
- [ ] **M39-012** — Support automatic halt and operator-approved rollback to an immutable previous revision set.
- [ ] **M39-013** — Prevent rollback to revoked/vulnerable versions even if they were previously active.
- [ ] **M39-014** — Record rollout state transitions, approvers, evidence, and revision IDs in audit/config provenance.
- [ ] **M39-015** — Ensure concurrent requests are pinned to one coherent configuration snapshot throughout processing.
- [ ] **M39-016** — Define emergency disable that stops new admissions without requiring unsafe bypass.
- [ ] **M39-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M39-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M39-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M39-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M39-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M39-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M39-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M39-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M39-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M39-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M39-027** — Inject a canary-only correctness/performance regression and verify automatic abort.
- [ ] **M39-028** — Test rollback during active high-volume validation and prove no mixed configuration per request.
- [ ] **M39-029** — Test control/canary observability and attribution across all key metrics.
- [ ] **M39-030** — Attempt rollback to an EOL/revoked build and require refusal.
- [ ] **M39-031** — Run full staged-rollout rehearsal in a production-like environment before first production activation.
- [ ] **M39-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M39-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M39-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M39-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M39-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M39-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M39-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M39-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M39-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M39-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M39-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M39-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M39-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M39-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M39-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M39-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M39-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M39-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M39-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M39-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M39-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M39: 52 items.**

## M40 — Operational runbooks [P2]

**Objective:** Provide executable operator procedures for bootstrap, deployment, normal operation, incident containment, rollback, cache/evidence recovery, and emergency actions.
**Primary dependencies/interfaces:** M27, M33, M38, M39, M41, M44
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M40-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Operational runbooks**; record escalation paths in M50.
- [ ] **M40-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M40-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M40-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M40-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M40-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M40-007** — Create Day-0 bootstrap steps covering trust roots, signed profiles/registries, service identity, storage, dependencies, health verification, and initial evidence seal.
- [ ] **M40-008** — Create Day-1 deployment steps with preflight checks, compatibility verification, canary progression, rollback point, and post-deploy validation.
- [ ] **M40-009** — Create Day-2 routines for capacity, alert review, key/profile/registry rotation, cache maintenance, evidence retention, and dependency health.
- [ ] **M40-010** — Create incident procedures for parser crash, unexpected accept/reject, provenance/signature failure, compromised engine, policy outage, audit failure, saturation, and tenant abuse.
- [ ] **M40-011** — Create profile/config rollback and emergency revocation procedures with exact authorization and audit requirements.
- [ ] **M40-012** — Document cache invalidation/rebuild and M44 state reconstruction steps.
- [ ] **M40-013** — Document evidence export/preservation for incident response without modifying original artifacts.
- [ ] **M40-014** — Define whether any break-glass path exists; validation bypass should be absent where possible, otherwise strictly time-bounded, independently approved, isolated, and audited.
- [ ] **M40-015** — Include exact health/metric/log/trace queries and expected states rather than vague “check logs” instructions.
- [ ] **M40-016** — Assign owner, review cadence, last-tested date, and linked game-day evidence to each runbook.
- [ ] **M40-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M40-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M40-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M40-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M40-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M40-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M40-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M40-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M40-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M40-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M40-027** — Execute every critical runbook in a game-day/test environment at least once before production sign-off.
- [ ] **M40-028** — Have an operator unfamiliar with the implementation follow runbooks and record ambiguities.
- [ ] **M40-029** — Test rollback/reconstruction using only documented steps and retained artifacts.
- [ ] **M40-030** — Validate contacts/escalation routes and permissions during a simulated critical incident.
- [ ] **M40-031** — Block release when mandatory runbooks are missing, stale beyond policy, or untested.
- [ ] **M40-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M40-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M40-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M40-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M40-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M40-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M40-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M40-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M40-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M40-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M40-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M40-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M40-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M40-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M40-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M40-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M40-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M40-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M40-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M40-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M40-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M40: 52 items.**

## M41 — Vulnerability response and EOL policy [P2]

**Objective:** Define supported-version windows, CVE triage/remediation, emergency revocation, and end-of-life enforcement for validator and runtime dependencies.
**Primary dependencies/interfaces:** M06, M21, M24, M39, M46
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M41-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Vulnerability response and EOL policy**; record escalation paths in M50.
- [ ] **M41-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M41-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M41-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M41-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M41-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M41-007** — Maintain an authoritative inventory of validator, runtime, parser libraries, crypto, OS/container, and other security-relevant dependency versions.
- [ ] **M41-008** — Define severity-based triage and remediation SLAs with explicit clock start, owner, and escalation path.
- [ ] **M41-009** — Subscribe to upstream security advisories and ecosystem vulnerability feeds relevant to every dependency.
- [ ] **M41-010** — Map advisories to exact deployed builds/compatibility matrix cells rather than package names alone.
- [ ] **M41-011** — Support emergency revocation of validator/engine/profile/spec entries and immediate blocking of new admissions on affected cells.
- [ ] **M41-012** — Define behavior for already-running workloads and retained attestations after revocation.
- [ ] **M41-013** — Publish support/EOL dates and minimum versions; prevent new deployment/admission on EOL revisions.
- [ ] **M41-014** — Require compensating-control waivers through M51 when remediation cannot meet SLA.
- [ ] **M41-015** — Verify replacement versions through conformance, determinism, performance, and staged rollout before broad promotion unless emergency procedures define a constrained exception.
- [ ] **M41-016** — Retain vulnerability decisions and evidence for auditability.
- [ ] **M41-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M41-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M41-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M41-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M41-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M41-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M41-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M41-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M41-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M41-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M41-027** — Run a simulated critical engine CVE and measure time to identify affected cells and block new admissions.
- [ ] **M41-028** — Test EOL enforcement in M21/M39/M52.
- [ ] **M41-029** — Verify SBOM/dependency inventory can identify exact exposure without manual source archaeology.
- [ ] **M41-030** — Exercise key/profile/runtime revocation propagation through caches and health/readiness.
- [ ] **M41-031** — Review closed incidents for SLA adherence and permanent prevention evidence.
- [ ] **M41-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M41-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M41-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M41-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M41-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M41-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M41-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M41-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M41-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M41-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M41-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M41-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M41-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M41-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M41-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M41-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M41-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M41-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M41-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M41-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M41-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M41: 52 items.**

## M42 — Configuration provenance store [P2]

**Objective:** Retain immutable authorship, approval, signature, revision, activation, and rollback lineage for every verdict-affecting configuration artifact.
**Primary dependencies/interfaces:** M05, M06, M13, M22, M23, M43, M44
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M42-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Configuration provenance store**; record escalation paths in M50.
- [ ] **M42-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M42-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M42-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M42-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M42-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M42-007** — Store profiles, spec registries, engine registries, limits, trust policy, and policy-integration configuration as immutable versioned objects.
- [ ] **M42-008** — Record content digest, schema version, author, signer, reviewers/approvers, creation time, activation time, supersedes/previous revision, and rollback target.
- [ ] **M42-009** — Verify signatures/digests on ingest and again before activation/use.
- [ ] **M42-010** — Prohibit in-place mutation of published revisions; corrections require a new revision linked to the prior one.
- [ ] **M42-011** — Provide tenant/environment scope and authorization metadata where configuration is not global.
- [ ] **M42-012** — Maintain append-only activation history so operators can reconstruct which exact revision set governed any historical request.
- [ ] **M42-013** — Protect store access with least privilege and separate authoring, approval, and activation permissions where risk warrants.
- [ ] **M42-014** — Replicate/backup immutable configuration independently from runtime caches.
- [ ] **M42-015** — Expose content-addressed retrieval for M37 historical explanation and M44 reconstruction.
- [ ] **M42-016** — Define retention long enough to validate retained attestations/audit records and legal/compliance requirements.
- [ ] **M42-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M42-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M42-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M42-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M42-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M42-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M42-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M42-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M42-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M42-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M42-027** — Attempt in-place mutation/deletion of active historical revisions and verify prevention/detection.
- [ ] **M42-028** — Reconstruct the exact configuration snapshot for sampled historical attestations.
- [ ] **M42-029** — Test unauthorized author/approver/activator identities and separation-of-duty rules.
- [ ] **M42-030** — Corrupt stored objects and require digest/signature failure.
- [ ] **M42-031** — Restore the provenance store from backup and verify all revision links and signatures.
- [ ] **M42-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M42-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M42-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M42-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M42-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M42-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M42-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M42-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M42-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M42-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M42-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M42-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M42-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M42-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M42-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M42-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M42-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M42-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M42-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M42-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M42-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M42: 52 items.**

## M43 — Atomic configuration activation [P2]

**Objective:** Validate and switch complete profile/spec/engine/limits/trust configuration sets atomically so requests never observe mixed revisions.
**Primary dependencies/interfaces:** M05, M06, M13, M22, M33, M39, M42
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M43-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Atomic configuration activation**; record escalation paths in M50.
- [ ] **M43-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M43-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M43-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M43-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M43-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M43-007** — Define an immutable configuration-bundle manifest that references exact content digests for every component of the active set.
- [ ] **M43-008** — Pre-validate schemas, signatures, dependency references, compatibility constraints, and local invariants before making a bundle eligible.
- [ ] **M43-009** — Stage artifacts completely before activation; never stream partial configuration into live readers.
- [ ] **M43-010** — Switch active bundle using an atomic pointer/generation mechanism appropriate to the storage/platform.
- [ ] **M43-011** — Pin each validation request to one bundle generation for its entire lifecycle.
- [ ] **M43-012** — Keep the previous approved bundle immediately available for rollback unless revoked.
- [ ] **M43-013** — Refuse activation when any referenced artifact is missing, corrupt, unsigned, incompatible, or outside validity policy.
- [ ] **M43-014** — Emit audit/config-provenance events for stage, validate, activate, rollback, and reject transitions.
- [ ] **M43-015** — Coordinate across replicated instances so rollout may be staged but each instance remains internally coherent.
- [ ] **M43-016** — Expose active generation/digests via M33/M35/M36.
- [ ] **M43-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M43-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M43-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M43-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M43-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M43-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M43-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M43-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M43-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M43-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M43-027** — Continuously send requests while activating/rolling back and prove each request uses exactly one generation.
- [ ] **M43-028** — Inject crash/power-loss between stage and activation and verify service recovers to a coherent generation.
- [ ] **M43-029** — Attempt activation with one corrupt/missing dependency and require no partial switch.
- [ ] **M43-030** — Test rollback to previous approved generation and attempted rollback to revoked generation.
- [ ] **M43-031** — Run concurrent activators and verify serialization/leader/compare-and-swap semantics prevent lost updates.
- [ ] **M43-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M43-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M43-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M43-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M43-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M43-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M43-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M43-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M43-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M43-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M43-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M43-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M43-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M43-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M43-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M43-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M43-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M43-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M43-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M43-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M43-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M43: 52 items.**

## M44 — Backup/reconstruction procedure [P2]

**Objective:** Rebuild caches, indices, and operational state from immutable artifacts and signed configuration without relying on mutable local state.
**Primary dependencies/interfaces:** M07, M08, M27, M42, M43
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M44-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Backup/reconstruction procedure**; record escalation paths in M50.
- [ ] **M44-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M44-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M44-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M44-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M44-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M44-007** — Classify state into authoritative immutable evidence/configuration versus disposable derived cache/index state.
- [ ] **M44-008** — Back up M42 provenance/configuration, required trust material, M27 audit/evidence references, and any attestation records required for compliance or admission history.
- [ ] **M44-009** — Define reconstruction order from trust roots → configuration revisions → immutable artifacts/evidence → indexes/caches.
- [ ] **M44-010** — Verify every restored object by digest/signature before using it.
- [ ] **M44-011** — Do not back up secrets in plaintext; use approved key-management backup/recovery procedures for signing/decryption keys.
- [ ] **M44-012** — Document recovery point objective and recovery time objective separately for authoritative evidence and disposable caches.
- [ ] **M44-013** — Make cache reconstruction safe to run empty; cache loss must reduce performance, not validation soundness.
- [ ] **M44-014** — Support clean-room rebuild into a fresh environment to detect hidden local-state dependencies.
- [ ] **M44-015** — Record restoration provenance and new environment identity without rewriting historical evidence.
- [ ] **M44-016** — Include disaster scenarios such as total local disk loss, database loss, region loss, and corrupted backup set.
- [ ] **M44-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M44-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M44-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M44-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M44-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M44-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M44-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M44-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M44-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M44-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M44-027** — Perform periodic full restore tests into fresh infrastructure and compare configuration/evidence digests.
- [ ] **M44-028** — Delete all caches/derived indexes and prove service can safely restart and repopulate them.
- [ ] **M44-029** — Restore from an older valid backup then replay immutable newer evidence/configuration to the target point.
- [ ] **M44-030** — Inject corrupt/missing backup objects and verify detection plus documented recovery escalation.
- [ ] **M44-031** — Measure actual RPO/RTO against requirements and track deviations.
- [ ] **M44-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M44-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M44-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M44-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M44-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M44-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M44-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M44-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M44-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M44-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M44-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M44-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M44-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M44-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M44-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M44-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M44-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M44-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M44-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M44-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M44-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M44: 52 items.**

## M45 — Package manifest / dependency pinning [P3]

**Objective:** Make the component installable and reproducible with explicit Python/runtime requirements, pk_core compatibility, and immutable dependency constraints.
**Primary dependencies/interfaces:** M41, M46, M47
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M45-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Package manifest / dependency pinning**; record escalation paths in M50.
- [ ] **M45-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M45-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M45-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M45-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M45-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M45-007** — Add a canonical package manifest declaring package name/version, supported Python versions, entry points, license, metadata, and build backend.
- [ ] **M45-008** — Declare `pk_core` as an explicit dependency/workspace binding with an approved version range or exact lock strategy instead of implicit environment discovery.
- [ ] **M45-009** — Pin direct and transitive dependencies through a reviewed lock/constraints mechanism suitable for reproducible builds.
- [ ] **M45-010** — Separate runtime, test, fuzz, benchmark, and development dependencies to minimize production attack surface.
- [ ] **M45-011** — Define supported platform/architecture markers and fail installation clearly on unsupported environments.
- [ ] **M45-012** — Ensure version is single-sourced and consistent across package metadata, runtime API, docs, changelog, and artifacts.
- [ ] **M45-013** — Generate hashes for downloaded/build dependencies where ecosystem tooling supports verified installs.
- [ ] **M45-014** — Prohibit unreviewed VCS/branch/URL floating dependencies in production builds.
- [ ] **M45-015** — Document offline/reproducible installation and local workspace development paths.
- [ ] **M45-016** — Add dependency update automation that opens reviewed changes and runs full conformance/security/performance gates.
- [ ] **M45-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M45-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M45-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M45-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M45-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M45-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M45-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M45-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M45-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M45-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M45-027** — Build/install from a clean environment using only the manifest/lock files.
- [ ] **M45-028** — Test all declared supported Python versions/platforms in CI.
- [ ] **M45-029** — Verify missing/incompatible pk_core fails with actionable diagnostics rather than silently skipping production gates.
- [ ] **M45-030** — Compare dependency graph against M46 SBOM and fail on drift.
- [ ] **M45-031** — Rebuild the same release twice from the same source/toolchain and compare package contents per M47.
- [ ] **M45-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M45-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M45-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M45-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M45-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M45-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M45-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M45-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M45-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M45-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M45-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M45-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M45-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M45-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M45-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M45-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M45-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M45-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M45-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M45-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M45-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M45: 52 items.**

## M46 — SBOM and license inventory [P3]

**Objective:** Produce a machine-readable dependency/software bill of materials and verified license/notice inventory for validator and associated runtime/tooling dependencies.
**Primary dependencies/interfaces:** M25, M41, M45, M47
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M46-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **SBOM and license inventory**; record escalation paths in M50.
- [ ] **M46-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M46-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M46-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M46-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M46-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M46-007** — Generate SBOM in at least one standard machine-readable format approved by the organization and include package name/version, supplier/source, hashes, dependency relationships, and component type.
- [ ] **M46-008** — Cover application code, Python/native dependencies, embedded binaries, parser/runtime libraries, container/base image packages, and build-time components as required by policy.
- [ ] **M46-009** — Generate from the resolved/installed build graph, not only declared top-level dependencies.
- [ ] **M46-010** — Bind SBOM digest to release artifact/provenance and M25 verification evidence.
- [ ] **M46-011** — Inventory declared licenses, copyright notices, source obligations, and incompatible/restricted licenses.
- [ ] **M46-012** — Retain required NOTICE/license texts in release packaging without exposing irrelevant source artifacts.
- [ ] **M46-013** — Detect unknown/no-license components and block release according to legal policy.
- [ ] **M46-014** — Scan SBOM against vulnerability intelligence as an input to M41, while recognizing scanner output requires triage.
- [ ] **M46-015** — Version and archive SBOM for each immutable release.
- [ ] **M46-016** — Validate SBOM itself for schema correctness, duplicate identities, and missing hashes where expected.
- [ ] **M46-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M46-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M46-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M46-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M46-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M46-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M46-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M46-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M46-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M46-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M46-027** — Compare SBOM against a clean installed environment and detect injected/removed dependency drift.
- [ ] **M46-028** — Test release gate with an unknown-license and policy-prohibited-license fixture.
- [ ] **M46-029** — Verify SBOM subject digest matches the release artifact it describes.
- [ ] **M46-030** — Use SBOM to identify exposure in a simulated dependency CVE.
- [ ] **M46-031** — Review generated license/NOTICE package in CI and release approval.
- [ ] **M46-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M46-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M46-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M46-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M46-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M46-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M46-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M46-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M46-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M46-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M46-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M46-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M46-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M46-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M46-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M46-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M46-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M46-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M46-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M46-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M46-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M46: 52 items.**

## M47 — Reproducible build metadata [P3]

**Objective:** Capture source, toolchain, environment, recipe, hashes, and deterministic packaging evidence sufficient to reproduce the validator release.
**Primary dependencies/interfaces:** M25, M45, M46
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M47-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Reproducible build metadata**; record escalation paths in M50.
- [ ] **M47-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M47-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M47-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M47-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M47-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M47-007** — Record immutable source revision, dirty-state policy, submodule/vendor revisions, build script digest, dependency lock digest, and package manifest version.
- [ ] **M47-008** — Record compiler/interpreter/build-tool versions, container/base image digest, target platform/architecture, locale/timezone, and relevant environment variables.
- [ ] **M47-009** — Normalize timestamps, file ordering, archive metadata, generated paths, locale-dependent output, and random build IDs where feasible.
- [ ] **M47-010** — Separate unavoidable non-deterministic signing/timestamp layers from reproducible unsigned payloads and document the envelope relationship.
- [ ] **M47-011** — Generate build manifest containing hashes of all release artifacts and supporting SBOM/profile/schema assets.
- [ ] **M47-012** — Produce provenance statement linking source and build recipe to output digests.
- [ ] **M47-013** — Build in an isolated environment with network access disabled after dependencies are materialized where feasible.
- [ ] **M47-014** — Detect undeclared generated files and workspace contamination in packaging.
- [ ] **M47-015** — Archive recipe and toolchain references long enough to reproduce supported releases.
- [ ] **M47-016** — Integrate reproducibility verification into release promotion rather than treating it as optional documentation.
- [ ] **M47-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M47-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M47-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M47-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M47-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M47-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M47-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M47-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M47-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M47-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M47-027** — Perform at least two independent clean builds and compare unsigned artifact digests/normalized contents.
- [ ] **M47-028** — Intentionally vary timezone, locale, working path, and build host and verify deterministic output or documented normalization.
- [ ] **M47-029** — Inject an undeclared workspace file and prove packaging/reproducibility checks detect it.
- [ ] **M47-030** — Verify provenance/SBOM subject hashes match final artifacts.
- [ ] **M47-031** — Reproduce a prior release using only archived source, lockfiles, recipe, and toolchain identifiers.
- [ ] **M47-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M47-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M47-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M47-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M47-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M47-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M47-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M47-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M47-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M47-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M47-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M47-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M47-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M47-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M47-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M47-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M47-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M47-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M47-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M47-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M47-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M47: 52 items.**

## M48 — Requirements traceability matrix [P3]

**Objective:** Map every INV-09-C001…C100 requirement to concrete implementation, configuration, test, benchmark, runbook, and evidence artifacts.
**Primary dependencies/interfaces:** M14, M15, M29, M40, M52
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M48-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Requirements traceability matrix**; record escalation paths in M50.
- [ ] **M48-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M48-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M48-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M48-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M48-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M48-007** — Create one row per requirement ID with normative requirement text, owner, implementation references, verification method, evidence artifact, status, and last-verified revision/date.
- [ ] **M48-008** — Require source/code references to specific module/function/schema/config sections rather than generic package-level links.
- [ ] **M48-009** — Require test references to specific test IDs/cases and distinguish unit, integration, fuzz, benchmark, certification, and operational evidence.
- [ ] **M48-010** — Link non-code requirements to runbooks, ADRs, policy/config, dashboards, audit evidence, or ownership records as appropriate.
- [ ] **M48-011** — Define status vocabulary such as NOT_IMPLEMENTED, IMPLEMENTED_UNVERIFIED, PASS, FAIL, BLOCKED, WAIVED, and NOT_APPLICABLE with strict semantics.
- [ ] **M48-012** — Prevent checklist completion based solely on inheritance/base-class generic results when concrete INV-09 evidence is absent.
- [ ] **M48-013** — Record exact evidence digest/revision so later edits do not rewrite historical pass claims.
- [ ] **M48-014** — Link waivers to M51 and prevent expired waivers from yielding PASS.
- [ ] **M48-015** — Automatically flag orphaned code/tests/evidence and requirements lacking current evidence.
- [ ] **M48-016** — Generate human-readable and machine-readable views from one canonical dataset.
- [ ] **M48-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M48-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M48-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M48-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M48-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M48-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M48-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M48-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M48-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M48-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M48-027** — Assert all 100 requirement IDs appear exactly once and no unknown IDs are silently ignored.
- [ ] **M48-028** — Delete/break a referenced test/evidence artifact and verify traceability validation fails.
- [ ] **M48-029** — Change a requirement or implementation revision and require re-verification according to impact rules.
- [ ] **M48-030** — Sample PASS rows and independently reproduce the linked evidence.
- [ ] **M48-031** — Feed matrix completeness/currentness directly into M52 with no manual “green” override.
- [ ] **M48-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M48-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M48-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M48-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M48-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M48-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M48-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M48-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M48-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M48-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M48-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M48-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M48-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M48-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M48-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M48-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M48-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M48-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M48-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M48-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M48-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M48: 52 items.**

## M49 — Architecture Decision Records [P3]

**Objective:** Preserve reviewed technical decisions and alternatives for specification baseline, feature profiles, determinism, parser/runtime choices, and compatibility policy.
**Primary dependencies/interfaces:** M05, M16, M21, M24
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M49-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Architecture Decision Records**; record escalation paths in M50.
- [ ] **M49-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M49-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M49-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M49-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M49-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M49-007** — Create ADRs for WebAssembly core/proposal baseline, raw parser/type-validator implementation strategy, feature taxonomy/profile model, determinism contract, runtime selection/hardening boundary, and compatibility certification policy.
- [ ] **M49-008** — Each ADR must include context, decision drivers, considered alternatives, decision, consequences, security implications, operational implications, and status.
- [ ] **M49-009** — Reference exact spec/tool/runtime revisions where the decision depends on external semantics.
- [ ] **M49-010** — Record rejected alternatives and why they failed requirements rather than only documenting the chosen design.
- [ ] **M49-011** — Include migration/rollback implications for decisions that affect persisted profiles, attestations, caches, or compatibility matrices.
- [ ] **M49-012** — Link relevant threat-model findings, benchmarks, prototypes, and test evidence.
- [ ] **M49-013** — Assign decision owner and approvers; security-sensitive decisions require security review.
- [ ] **M49-014** — Use immutable identifiers and supersede old ADRs instead of rewriting historical rationale.
- [ ] **M49-015** — Trigger ADR review when a foundational assumption changes, such as new Wasm proposal support or runtime replacement.
- [ ] **M49-016** — Link ADR IDs from code/config schemas where a non-obvious invariant is enforced.
- [ ] **M49-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M49-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M49-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M49-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M49-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M49-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M49-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M49-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M49-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M49-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M49-027** — Review all production-critical design choices and verify each has an active/superseded ADR.
- [ ] **M49-028** — Check ADR references/links and external revision identifiers during release documentation validation.
- [ ] **M49-029** — Perform architecture review using ADRs to reconstruct why the current design exists without relying on tribal knowledge.
- [ ] **M49-030** — Verify superseded decisions have explicit migration impact and no stale “accepted” status.
- [ ] **M49-031** — Include ADR-currentness as M52 governance evidence.
- [ ] **M49-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M49-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M49-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M49-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M49-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M49-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M49-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M49-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M49-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M49-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M49-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M49-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M49-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M49-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M49-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M49-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M49-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M49-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M49-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M49-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M49-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M49: 52 items.**

## M50 — Named ownership and escalation [P3]

**Objective:** Assign accountable technical, security, runtime, operations, and incident ownership with an actionable escalation model.
**Primary dependencies/interfaces:** M38, M40, M41, M51, M52
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M50-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Named ownership and escalation**; record escalation paths in M50.
- [ ] **M50-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M50-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M50-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M50-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M50-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M50-007** — Name a service/component owner accountable for availability, correctness, roadmap, and production readiness.
- [ ] **M50-008** — Name a security owner accountable for threat model, vulnerability response, trust/signing policy, and security exceptions.
- [ ] **M50-009** — Name a runtime owner for engine capability, sandbox hardening, compatibility, and CVE posture.
- [ ] **M50-010** — Define primary/secondary on-call or incident response routes and time-zone/coverage expectations.
- [ ] **M50-011** — Define incident severity levels and entry criteria specific to validation bypass, false accept, widespread false reject, security compromise, and outage.
- [ ] **M50-012** — Define who may approve profile/spec/engine changes, production release, rollback, emergency revocation, and M51 waivers.
- [ ] **M50-013** — Use role/group identities rather than single-person-only dependencies where practical, while retaining accountable approvers.
- [ ] **M50-014** — Maintain contact/escalation data in a controlled system and reference it from runbooks/alerts without duplicating stale copies.
- [ ] **M50-015** — Define handoff process for personnel/team changes and require ownership recertification periodically.
- [ ] **M50-016** — Escalate unowned critical findings automatically to release NO_GO.
- [ ] **M50-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M50-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M50-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M50-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M50-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M50-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M50-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M50-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M50-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M50-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M50-027** — Run an escalation drill from alert to accountable owner and measure response path.
- [ ] **M50-028** — Verify every critical dashboard alert and runbook resolves to a current owner/on-call route.
- [ ] **M50-029** — Test permissions match declared approval authority and former owners lose privileged access promptly.
- [ ] **M50-030** — Audit ownership gaps quarterly/at release.
- [ ] **M50-031** — Require M52 to fail when mandatory owner/approval records are missing or stale.
- [ ] **M50-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M50-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M50-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M50-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M50-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M50-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M50-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M50-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M50-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M50-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M50-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M50-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M50-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M50-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M50-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M50-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M50-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M50-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M50-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M50-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M50-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M50: 52 items.**

## M51 — Exception/waiver register [P3]

**Objective:** Govern every production deviation with explicit scope, rationale, compensating controls, risk owner, expiration, and reapproval.
**Primary dependencies/interfaces:** M28, M30, M41, M48, M50, M52
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M51-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Exception/waiver register**; record escalation paths in M50.
- [ ] **M51-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M51-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M51-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M51-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M51-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M51-007** — Define a machine-readable waiver schema with ID, requirement/control, affected versions/environments/tenants, rationale, risk statement, compensating controls, owner, approvers, issue date, expiry, and review cadence.
- [ ] **M51-008** — Prohibit permanent/expiry-free waivers for security-critical production controls unless governance explicitly defines an exceptional category.
- [ ] **M51-009** — Require narrower scope than the underlying control whenever technically possible.
- [ ] **M51-010** — Bind waiver applicability to exact version/configuration/profile context so it cannot silently expand after upgrades.
- [ ] **M51-011** — Require security approval for security controls and performance/operations approval for relevant domains.
- [ ] **M51-012** — Track remediation plan and target milestone; a waiver is not a substitute for backlog ownership.
- [ ] **M51-013** — Surface active waivers in M37/M38/M52 at the appropriate authorization level.
- [ ] **M51-014** — Automatically invalidate expired waivers and prevent release/admission decisions from treating them as active.
- [ ] **M51-015** — Preserve historical waivers and approvals immutably for audit.
- [ ] **M51-016** — Define emergency waiver issuance with shorter expiry and mandatory post-incident review.
- [ ] **M51-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M51-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M51-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M51-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M51-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M51-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M51-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M51-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M51-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M51-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M51-027** — Test scope matching so a waiver for one version/profile/tenant cannot authorize another.
- [ ] **M51-028** — Expire a waiver and verify M48/M52 status changes automatically.
- [ ] **M51-029** — Remove a compensating control and require waiver re-evaluation/failure.
- [ ] **M51-030** — Audit a sample of active waivers for owner, approval, evidence, and remediation progress.
- [ ] **M51-031** — Test emergency waiver workflow and ensure it cannot bypass non-waivable controls such as fundamental validation identity without explicit governance.
- [ ] **M51-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M51-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M51-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M51-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M51-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M51-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M51-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M51-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M51-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M51-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M51-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M51-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M51-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M51-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M51-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M51-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M51-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M51-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M51-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M51-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M51-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M51: 52 items.**

## M52 — Formal production exit gate [P3]

**Objective:** Compute a machine-readable GO/NO_GO decision that requires current evidence for parser/type validation, security, determinism, compatibility, performance, observability, rollback, provenance, and ownership.
**Primary dependencies/interfaces:** M01, M02, M08, M14, M15, M20, M21, M30, M38, M39, M40, M41, M44, M48, M50, M51
**Completion rule:** This component is not complete until every mandatory checkbox below is satisfied or an approved, unexpired M51 waiver is linked to the exact item and scope.

### A. Requirements, contracts, and threat boundaries
- [ ] **M52-001** — Assign an accountable implementation owner, security reviewer, and operational owner for **Formal production exit gate**; record escalation paths in M50.
- [ ] **M52-002** — Write normative MUST/SHOULD/MUST-NOT requirements and explicit non-goals; distinguish security invariants from implementation preferences.
- [ ] **M52-003** — Define all trust boundaries, untrusted inputs, trusted upstream facts, downstream consumers, attacker capabilities, and fail-closed behavior for malformed or unavailable dependencies.
- [ ] **M52-004** — Define a versioned machine-readable interface/schema for all externally consumed inputs/outputs/configuration; reject unknown or ambiguous fields according to compatibility policy.
- [ ] **M52-005** — Identify every verdict-affecting datum and require an immutable revision, digest, or authenticated identity suitable for M08 attestations and M09 cache keys.
- [ ] **M52-006** — Define maximum sizes/counts/depths/time budgets for attacker-controlled data before implementation, and link enforceable limits to M13 where relevant.

### B. Architecture and implementation
- [ ] **M52-007** — Define a signed/versioned gate policy enumerating mandatory evidence classes, freshness windows, severity thresholds, waiver rules, and environment/release scope.
- [ ] **M52-008** — Consume M48 traceability status plus explicit parser/type-validator, fuzz/differential, determinism, compatibility, performance, security, provenance, operations, and ownership evidence.
- [ ] **M52-009** — Treat missing, stale, corrupt, unsigned, unverifiable, or incompatible evidence as failure rather than “unknown/pass”.
- [ ] **M52-010** — Require zero unresolved critical/high false-accept/security defects according to governance policy.
- [ ] **M52-011** — Require only currently supported/non-revoked validator/runtime/profile/spec matrix cells.
- [ ] **M52-012** — Require M30 performance gate, M39 rollout readiness, M40 runbooks, M41 vulnerability posture, and M44 recovery evidence to be current.
- [ ] **M52-013** — Evaluate M51 waivers explicitly and reject expired/out-of-scope/unauthorized waivers.
- [ ] **M52-014** — Produce a deterministic gate result with per-control PASS/FAIL/BLOCKED/WAIVED status and immutable evidence references.
- [ ] **M52-015** — Sign/seal the gate result and bind it to release artifact digest and configuration bundle revision.
- [ ] **M52-016** — Integrate the gate as a hard release/deployment control with no ordinary manual “force green” path.
- [ ] **M52-017** — Use immutable/internal typed representations after trust-boundary validation; do not pass raw unvalidated dictionaries/strings deeper into security decisions when a constrained type is possible.
- [ ] **M52-018** — Make error paths explicit and deterministic; convert implementation exceptions into M12 structured failure codes at the component boundary.
- [ ] **M52-019** — Ensure cancellation, deadline, shutdown, and retry behavior cannot convert an indeterminate or partial result into successful validation/admission.
- [ ] **M52-020** — Document concurrency/thread-safety/reentrancy semantics and protect shared mutable state with an architecture that can be race-tested.

### C. Security and hardening
- [ ] **M52-021** — Perform a component-specific threat-model review covering spoofing, tampering, replay, downgrade, confused-deputy behavior, resource exhaustion, cross-tenant leakage, and unsafe recovery paths as applicable.
- [ ] **M52-022** — Fail closed for unknown versions/features/states, invalid signatures/digests, partial data, stale security state, and dependency ambiguity unless a narrowly documented safe fallback exists.
- [ ] **M52-023** — Use overflow-safe arithmetic, bounded allocation, bounded recursion/work, length-prefixed decoding checks, and canonical comparisons anywhere attacker-controlled sizes or identifiers are processed.
- [ ] **M52-024** — Apply least privilege to filesystem, network, signing keys, service identities, caches, configuration, and observability access used by this component.
- [ ] **M52-025** — Ensure attacker-controlled strings/bytes cannot create log injection, path traversal, code execution, shell invocation, unsafe deserialization, or unbounded diagnostic output.
- [ ] **M52-026** — Define secrets/data-classification rules and prove raw module bytes, tenant-confidential metadata, credentials, and private key material are not exposed through logs/metrics/errors/traces.

### D. Verification and negative testing
- [ ] **M52-027** — Remove each mandatory evidence class in turn and verify the gate returns NO_GO/BLOCKED.
- [ ] **M52-028** — Feed stale/revoked/mismatched evidence and require failure.
- [ ] **M52-029** — Test valid and expired waivers with exact scope matching.
- [ ] **M52-030** — Recompute a gate from archived immutable evidence and verify the same deterministic result.
- [ ] **M52-031** — Attempt release/deployment with a failed gate and prove the delivery system blocks promotion.
- [ ] **M52-032** — Add unit tests for every normative branch and boundary condition, including zero, one, maximum-allowed, maximum+1, malformed type, missing field, unknown enum, and stale revision cases where applicable.
- [ ] **M52-033** — Add integration tests that exercise upstream and downstream interfaces using the exact production schemas and trust material format.
- [ ] **M52-034** — Add regression tests for every discovered defect/security finding and keep the reproducer permanently linked to its issue/CVE/finding ID.
- [ ] **M52-035** — Run tests in release/optimized mode as well as ordinary test mode and require equivalent security verdicts.
- [ ] **M52-036** — Measure code/branch/path coverage as a diagnostic and review uncovered security-relevant branches manually; do not use coverage percentage as the sole acceptance criterion.

### E. Observability, operations, and lifecycle
- [ ] **M52-037** — Emit bounded-cardinality M34 metrics for success/refusal/error, latency, saturation/resource use, and component-specific exceptional states.
- [ ] **M52-038** — Emit M35 structured logs and M36 trace spans with operation/trace IDs, module digest, active configuration revisions, and M12 error code while respecting redaction policy.
- [ ] **M52-039** — Emit M27 audit events for security-relevant configuration changes, refusals, bypass attempts, revocations, or other privileged transitions owned by this component.
- [ ] **M52-040** — Expose readiness/degraded status through M33 when this component or one of its mandatory dependencies cannot safely serve production requests.
- [ ] **M52-041** — Add component-specific dashboard panels/alerts in M38 and link each actionable alert to an M40 runbook and current owner.
- [ ] **M52-042** — Define upgrade, rollback, schema migration, deprecation, EOL, and emergency-revocation behavior; preserve the ability to interpret historical evidence.
- [ ] **M52-043** — Document capacity assumptions and verify benchmark/soak/fault behavior through M29/M31/M32 where the component is on the validation/admission critical path.

### F. Documentation, evidence, and release gating
- [ ] **M52-044** — Create or update the architecture/design document with data flow, state model, trust boundaries, invariants, failure modes, dependency diagram, and rationale; link relevant M49 ADRs.
- [ ] **M52-045** — Add operator and developer documentation including configuration examples, safe defaults, forbidden configurations, troubleshooting, and rollback/recovery procedures.
- [ ] **M52-046** — Map the implementation and its tests/evidence into M48 requirements traceability with immutable artifact references.
- [ ] **M52-047** — Include source revision, build/toolchain identity, dependency/SBOM references, configuration revision, and test evidence in the release evidence bundle.
- [ ] **M52-048** — Run static analysis/lint/type checks, dependency/security scans, unit/integration tests, and package integrity verification with zero unexplained critical/high findings.
- [ ] **M52-049** — Pass the component-specific CI gate from a clean environment with no reliance on undeclared local state, developer caches, or network-fetched floating dependencies.

### G. Definition of Done
- [ ] **M52-050** — All mandatory checklist items above are PASS with linked evidence, or the exact item has a valid M51 waiver with owner, compensating control, scope, and expiration.
- [ ] **M52-051** — No unresolved critical/high-severity correctness or security finding can cause a false ACCEPT, validation bypass, evidence misbinding, cross-tenant breach, or uncontrolled resource exhaustion.
- [ ] **M52-052** — M52 consumes current evidence for this component and returns PASS/approved-WAIVED for the intended release and deployment scope; otherwise production promotion remains NO_GO.

**Checklist count for M52: 52 items.**

---

## Master completion summary

- **Components:** 52
- **Total atomic checklist items:** 2704
- **P0 checklist items:** 780
- **P1 checklist items:** 676
- **P2 checklist items:** 832
- **P3 checklist items:** 416

### Production exit interpretation

INV-09 must remain **NO_GO as a production WebAssembly validation boundary** until the P0 chain establishes trustworthy byte-derived parsing, typing, feature facts, artifact identity, attestation, safe caching, and mandatory execution admission. P1–P3 controls then establish deterministic/host behavior, compatibility, operational resilience, observability, supply-chain integrity, ownership, and auditable release governance. The existing v4.2.0 descriptor-level policy kernel is useful as one layer of this system but does not replace the P0 byte-level trust boundary.

### Evidence package expected at final gate

- [ ] Signed release artifact + M07 module/artifact digests and M47 reproducible build metadata.
- [ ] M45 package manifest/locks and M46 SBOM/license inventory.
- [ ] M05/M06/M22/M42/M43 signed active configuration bundle and activation provenance.
- [ ] M14 fuzz corpus/results and M15 differential-validation disposition report.
- [ ] M20 determinism certification and M21 supported compatibility matrix.
- [ ] M29 benchmark results, M30 performance gate, M31 soak evidence, and M32 fault-injection report.
- [ ] M33–M38 operational telemetry contracts, dashboards, alerts, and explainability evidence.
- [ ] M39 rollout/rollback evidence, M40 runbook game-day results, M41 vulnerability posture, and M44 restore test.
- [ ] M48 complete 100-requirement traceability matrix, M49 ADR set, M50 ownership records, and M51 active waiver register.
- [ ] M52 signed machine-readable production gate result bound to the exact release digest and configuration revision.