# INV-12 Language Interoperability — Professional Missing-Components Checklist

**Baseline:** INV-12 v4.2.0 hardened  
**Checklist pack:** v1.0.0  
**Coverage:** 58 missing components × 56 technical controls = 3,248 component controls, plus 290 component Definition-of-Done gates and 12 program gates.  
**Status:** `- [ ]` means evidence is still required; change to `- [x]` only when objective evidence exists.

## Evidence and completion policy

- Each control should produce reviewable evidence: source, tests, design records, CI logs, signed artifacts, metrics, runbooks, or measured results.
- P0/P1 correctness, memory/resource-safety, authentication/authorization, provenance, compatibility, or rollback defects block Production GO.
- “Implemented” is not enough: implementation, negative-path tests, integration behavior, and retained evidence must agree.
- N/A requires an explicit waiver with scope, rationale, risk owner, reviewer, and expiry/review date.
- Preserve stable IDs below in tickets, commits, CI jobs, requirements traceability, and release evidence.

## Index

- **MC-001 — Canonical type AST and schema loader** — ABI Semantics
- **MC-002 — Complete canonical primitive type set** — ABI Semantics
- **MC-003 — Tuple, enum, and flags model** — ABI Semantics
- **MC-004 — Resource-handle type system** — ABI Semantics
- **MC-005 — Own/borrow semantics** — ABI Semantics
- **MC-006 — Recursive composite validator** — ABI Semantics
- **MC-007 — Language representation registry** — ABI Semantics
- **MC-008 — Numeric conversion policy engine** — ABI Semantics
- **MC-009 — Unicode and character transcoder** — ABI Semantics
- **MC-010 — Canonical binary layout engine** — ABI Semantics
- **MC-011 — Guest-memory adapter** — Runtime & Language Integration
- **MC-012 — Realloc/post-return lifecycle** — Runtime & Language Integration
- **MC-013 — Variant/option/result wire model** — ABI Semantics
- **MC-014 — Canonical error envelope** — ABI Semantics
- **MC-015 — ABI/version negotiation** — ABI Semantics
- **MC-016 — Compatibility/evolution engine** — ABI Semantics
- **MC-017 — Async/future/stream boundary semantics** — ABI Semantics
- **MC-018 — Schema-derived resource limits** — Security & Policy
- **MC-019 — WebAssembly Component Model runtime adapter** — Runtime & Language Integration
- **MC-020 — Rust binding adapter and fixture component** — Runtime & Language Integration
- **MC-021 — Go binding adapter and fixture component** — Runtime & Language Integration
- **MC-022 — JavaScript binding adapter and fixture component** — Runtime & Language Integration
- **MC-023 — Python binding adapter and fixture component** — Runtime & Language Integration
- **MC-024 — Cross-language conformance matrix** — Verification & Certification
- **MC-025 — Adjacent-layer integration fixtures** — Verification & Certification
- **MC-026 — Golden canonical test-vector corpus** — Verification & Certification
- **MC-027 — Property-based test harness** — Verification & Certification
- **MC-028 — Coverage-guided fuzzing harness** — Verification & Certification
- **MC-029 — Differential runtime tester** — Verification & Certification
- **MC-030 — Malicious-memory test harness** — Verification & Certification
- **MC-031 — Concurrency/race stress suite** — Verification & Certification
- **MC-032 — Leak/use-after-free detector integration** — Verification & Certification
- **MC-033 — Cross-platform architecture matrix** — Verification & Certification
- **MC-034 — Performance benchmark harness** — Verification & Certification
- **MC-035 — SLO certification gate** — Verification & Certification
- **MC-036 — Large-payload/DoS benchmark suite** — Verification & Certification
- **MC-037 — Metrics emitter** — Observability & Operations
- **MC-038 — Distributed trace instrumentation** — Observability & Operations
- **MC-039 — Structured security audit events** — Security & Policy
- **MC-040 — Diagnostic redaction policy** — Security & Policy
- **MC-041 — Runtime health/readiness model** — Observability & Operations
- **MC-042 — Capacity/fairness controller** — Observability & Operations
- **MC-043 — Declarative configuration schema** — Configuration & Governance
- **MC-044 — Configuration validator/transaction manager** — Configuration & Governance
- **MC-045 — Mapping-policy provenance** — Supply Chain & Trust
- **MC-046 — Artifact provenance verifier** — Supply Chain & Trust
- **MC-047 — SBOM and dependency lock** — Supply Chain & Trust
- **MC-048 — Capability/authentication integration** — Security & Policy
- **MC-049 — Trust-service outage policy** — Security & Policy
- **MC-050 — Architecture Decision Record** — Documentation & Release Governance
- **MC-051 — Formal threat model** — Documentation & Release Governance
- **MC-052 — Requirements traceability matrix** — Documentation & Release Governance
- **MC-053 — Reproducible pk_core integration environment** — Build & CI
- **MC-054 — CI conformance pipeline** — Build & CI
- **MC-055 — Release evidence bundle** — Documentation & Release Governance
- **MC-056 — Compatibility support matrix** — Documentation & Release Governance
- **MC-057 — Rollback and emergency-disable runbook** — Operations & Incident Response
- **MC-058 — Operational incident playbook** — Operations & Incident Response

---

## MC-001 — Canonical type AST and schema loader

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Canonical type AST and schema loader` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-001-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-001-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-001-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-001-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-001-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-001-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-001-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-001-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-001-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-001-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-001-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-001-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-001-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-001-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-001-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-001-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-001-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-001-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-001-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-001-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-001-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-001-22** — Define a formal grammar or schema meta-model with source-location preservation and deterministic normalization.
- [ ] **MC-001-23** — Reject duplicate/ambiguous declarations, illegal recursion, unresolved references, and version-incompatible imports.
- [ ] **MC-001-24** — Guarantee parse → normalize → serialize determinism with golden fixtures and stable canonical hashes.
- [ ] **MC-001-25** — Produce a normative design subsection specific to **Canonical type AST and schema loader** with valid and invalid worked examples.
- [ ] **MC-001-26** — Create an end-to-end integration fixture proving **Canonical type AST and schema loader** works through its real production-facing path.

### E. Implementation

- [ ] **MC-001-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-001-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-001-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-001-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-001-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-001-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-001-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-001-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-001-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-001-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-001-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-001-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-001-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-001-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-001-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-001-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-001-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-001-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-001-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-001-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-001-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-001-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-001-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-001-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-001-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-001-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-001-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-001-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-001-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-001-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-001-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-001-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-001-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-001-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-001-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-002 — Complete canonical primitive type set

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Complete canonical primitive type set` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-002-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-002-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-002-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-002-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-002-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-002-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-002-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-002-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-002-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-002-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-002-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-002-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-002-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-002-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-002-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-002-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-002-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-002-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-002-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-002-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-002-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-002-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.
- [ ] **MC-002-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.
- [ ] **MC-002-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.
- [ ] **MC-002-25** — Produce a normative design subsection specific to **Complete canonical primitive type set** with valid and invalid worked examples.
- [ ] **MC-002-26** — Create an end-to-end integration fixture proving **Complete canonical primitive type set** works through its real production-facing path.

### E. Implementation

- [ ] **MC-002-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-002-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-002-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-002-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-002-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-002-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-002-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-002-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-002-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-002-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-002-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-002-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-002-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-002-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-002-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-002-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-002-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-002-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-002-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-002-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-002-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-002-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-002-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-002-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-002-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-002-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-002-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-002-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-002-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-002-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-002-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-002-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-002-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-002-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-002-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-003 — Tuple, enum, and flags model

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Tuple, enum, and flags model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-003-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-003-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-003-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-003-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-003-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-003-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-003-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-003-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-003-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-003-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-003-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-003-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-003-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-003-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-003-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-003-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-003-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-003-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-003-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-003-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-003-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-003-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.
- [ ] **MC-003-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.
- [ ] **MC-003-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.
- [ ] **MC-003-25** — Produce a normative design subsection specific to **Tuple, enum, and flags model** with valid and invalid worked examples.
- [ ] **MC-003-26** — Create an end-to-end integration fixture proving **Tuple, enum, and flags model** works through its real production-facing path.

### E. Implementation

- [ ] **MC-003-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-003-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-003-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-003-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-003-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-003-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-003-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-003-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-003-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-003-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-003-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-003-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-003-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-003-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-003-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-003-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-003-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-003-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-003-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-003-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-003-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-003-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-003-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-003-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-003-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-003-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-003-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-003-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-003-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-003-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-003-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-003-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-003-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-003-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-003-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-004 — Resource-handle type system

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Resource-handle type system` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-004-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-004-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-004-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-004-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-004-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-004-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-004-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-004-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-004-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-004-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-004-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-004-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-004-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-004-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-004-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-004-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-004-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-004-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-004-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-004-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-004-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-004-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.
- [ ] **MC-004-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.
- [ ] **MC-004-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.
- [ ] **MC-004-25** — Produce a normative design subsection specific to **Resource-handle type system** with valid and invalid worked examples.
- [ ] **MC-004-26** — Create an end-to-end integration fixture proving **Resource-handle type system** works through its real production-facing path.

### E. Implementation

- [ ] **MC-004-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-004-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-004-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-004-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-004-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-004-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-004-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-004-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-004-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-004-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-004-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-004-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-004-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-004-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-004-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-004-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-004-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-004-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-004-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-004-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-004-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-004-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-004-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-004-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-004-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-004-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-004-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-004-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-004-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-004-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-004-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-004-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-004-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-004-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-004-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-005 — Own/borrow semantics

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Own/borrow semantics` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-005-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-005-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-005-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-005-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-005-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-005-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-005-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-005-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-005-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-005-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-005-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-005-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-005-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-005-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-005-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-005-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-005-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-005-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-005-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-005-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-005-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-005-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.
- [ ] **MC-005-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.
- [ ] **MC-005-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.
- [ ] **MC-005-25** — Produce a normative design subsection specific to **Own/borrow semantics** with valid and invalid worked examples.
- [ ] **MC-005-26** — Create an end-to-end integration fixture proving **Own/borrow semantics** works through its real production-facing path.

### E. Implementation

- [ ] **MC-005-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-005-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-005-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-005-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-005-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-005-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-005-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-005-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-005-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-005-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-005-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-005-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-005-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-005-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-005-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-005-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-005-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-005-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-005-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-005-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-005-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-005-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-005-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-005-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-005-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-005-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-005-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-005-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-005-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-005-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-005-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-005-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-005-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-005-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-005-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-006 — Recursive composite validator

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Recursive composite validator` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-006-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-006-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-006-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-006-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-006-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-006-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-006-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-006-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-006-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-006-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-006-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-006-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-006-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-006-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-006-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-006-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-006-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-006-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-006-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-006-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-006-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-006-22** — Produce a normative design subsection specific to **Recursive composite validator** with valid and invalid worked examples.
- [ ] **MC-006-23** — Create an end-to-end integration fixture proving **Recursive composite validator** works through its real production-facing path.
- [ ] **MC-006-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Recursive composite validator** and enforce them automatically.
- [ ] **MC-006-25** — Record assumptions and unsupported cases for **Recursive composite validator** in machine-readable release metadata where practical.
- [ ] **MC-006-26** — Create at least one failure-injection scenario for **Recursive composite validator** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-006-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-006-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-006-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-006-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-006-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-006-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-006-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-006-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-006-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-006-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-006-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-006-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-006-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-006-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-006-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-006-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-006-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-006-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-006-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-006-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-006-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-006-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-006-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-006-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-006-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-006-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-006-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-006-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-006-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-006-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-006-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-006-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-006-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-006-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-006-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-007 — Language representation registry

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Language representation registry` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-007-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-007-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-007-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-007-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-007-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-007-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-007-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-007-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-007-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-007-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-007-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-007-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-007-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-007-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-007-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-007-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-007-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-007-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-007-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-007-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-007-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-007-22** — Produce a normative design subsection specific to **Language representation registry** with valid and invalid worked examples.
- [ ] **MC-007-23** — Create an end-to-end integration fixture proving **Language representation registry** works through its real production-facing path.
- [ ] **MC-007-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Language representation registry** and enforce them automatically.
- [ ] **MC-007-25** — Record assumptions and unsupported cases for **Language representation registry** in machine-readable release metadata where practical.
- [ ] **MC-007-26** — Create at least one failure-injection scenario for **Language representation registry** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-007-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-007-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-007-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-007-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-007-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-007-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-007-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-007-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-007-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-007-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-007-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-007-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-007-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-007-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-007-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-007-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-007-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-007-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-007-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-007-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-007-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-007-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-007-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-007-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-007-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-007-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-007-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-007-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-007-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-007-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-007-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-007-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-007-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-007-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-007-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-008 — Numeric conversion policy engine

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Numeric conversion policy engine` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-008-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-008-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-008-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-008-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-008-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-008-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-008-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-008-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-008-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-008-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-008-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-008-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-008-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-008-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-008-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-008-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-008-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-008-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-008-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-008-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-008-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-008-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.
- [ ] **MC-008-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.
- [ ] **MC-008-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.
- [ ] **MC-008-25** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.
- [ ] **MC-008-26** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.

### E. Implementation

- [ ] **MC-008-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-008-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-008-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-008-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-008-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-008-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-008-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-008-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-008-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-008-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-008-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-008-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-008-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-008-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-008-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-008-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-008-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-008-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-008-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-008-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-008-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-008-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-008-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-008-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-008-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-008-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-008-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-008-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-008-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-008-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-008-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-008-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-008-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-008-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-008-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-009 — Unicode and character transcoder

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Unicode and character transcoder` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-009-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-009-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-009-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-009-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-009-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-009-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-009-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-009-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-009-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-009-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-009-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-009-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-009-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-009-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-009-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-009-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-009-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-009-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-009-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-009-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-009-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-009-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.
- [ ] **MC-009-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.
- [ ] **MC-009-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.
- [ ] **MC-009-25** — Produce a normative design subsection specific to **Unicode and character transcoder** with valid and invalid worked examples.
- [ ] **MC-009-26** — Create an end-to-end integration fixture proving **Unicode and character transcoder** works through its real production-facing path.

### E. Implementation

- [ ] **MC-009-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-009-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-009-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-009-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-009-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-009-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-009-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-009-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-009-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-009-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-009-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-009-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-009-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-009-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-009-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-009-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-009-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-009-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-009-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-009-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-009-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-009-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-009-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-009-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-009-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-009-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-009-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-009-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-009-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-009-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-009-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-009-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-009-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-009-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-009-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-010 — Canonical binary layout engine

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Canonical binary layout engine` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-010-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-010-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-010-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-010-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-010-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-010-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-010-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-010-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-010-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-010-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-010-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-010-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-010-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-010-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-010-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-010-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-010-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-010-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-010-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-010-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-010-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-010-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.
- [ ] **MC-010-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.
- [ ] **MC-010-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.
- [ ] **MC-010-25** — Produce a normative design subsection specific to **Canonical binary layout engine** with valid and invalid worked examples.
- [ ] **MC-010-26** — Create an end-to-end integration fixture proving **Canonical binary layout engine** works through its real production-facing path.

### E. Implementation

- [ ] **MC-010-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-010-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-010-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-010-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-010-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-010-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-010-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-010-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-010-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-010-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-010-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-010-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-010-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-010-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-010-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-010-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-010-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-010-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-010-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-010-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-010-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-010-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-010-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-010-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-010-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-010-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-010-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-010-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-010-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-010-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-010-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-010-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-010-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-010-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-010-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-011 — Guest-memory adapter

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Guest-memory adapter` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-011-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-011-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-011-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-011-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-011-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-011-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-011-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-011-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-011-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-011-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-011-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-011-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-011-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-011-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-011-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-011-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-011-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-011-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-011-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-011-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-011-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-011-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.
- [ ] **MC-011-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.
- [ ] **MC-011-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.
- [ ] **MC-011-25** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-011-26** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.

### E. Implementation

- [ ] **MC-011-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-011-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-011-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-011-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-011-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-011-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-011-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-011-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-011-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-011-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-011-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-011-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-011-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-011-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-011-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-011-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-011-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-011-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-011-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-011-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-011-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-011-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-011-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-011-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-011-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-011-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-011-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-011-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-011-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-011-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-011-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-011-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-011-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-011-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-011-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-012 — Realloc/post-return lifecycle

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Realloc/post-return lifecycle` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-012-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-012-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-012-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-012-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-012-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-012-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-012-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-012-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-012-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-012-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-012-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-012-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-012-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-012-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-012-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-012-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-012-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-012-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-012-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-012-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-012-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-012-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.
- [ ] **MC-012-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.
- [ ] **MC-012-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.
- [ ] **MC-012-25** — Produce a normative design subsection specific to **Realloc/post-return lifecycle** with valid and invalid worked examples.
- [ ] **MC-012-26** — Create an end-to-end integration fixture proving **Realloc/post-return lifecycle** works through its real production-facing path.

### E. Implementation

- [ ] **MC-012-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-012-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-012-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-012-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-012-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-012-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-012-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-012-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-012-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-012-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-012-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-012-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-012-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-012-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-012-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-012-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-012-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-012-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-012-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-012-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-012-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-012-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-012-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-012-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-012-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-012-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-012-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-012-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-012-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-012-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-012-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-012-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-012-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-012-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-012-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-013 — Variant/option/result wire model

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Variant/option/result wire model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-013-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-013-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-013-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-013-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-013-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-013-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-013-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-013-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-013-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-013-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-013-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-013-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-013-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-013-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-013-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-013-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-013-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-013-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-013-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-013-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-013-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-013-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.
- [ ] **MC-013-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.
- [ ] **MC-013-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.
- [ ] **MC-013-25** — Produce a normative design subsection specific to **Variant/option/result wire model** with valid and invalid worked examples.
- [ ] **MC-013-26** — Create an end-to-end integration fixture proving **Variant/option/result wire model** works through its real production-facing path.

### E. Implementation

- [ ] **MC-013-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-013-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-013-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-013-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-013-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-013-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-013-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-013-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-013-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-013-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-013-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-013-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-013-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-013-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-013-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-013-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-013-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-013-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-013-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-013-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-013-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-013-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-013-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-013-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-013-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-013-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-013-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-013-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-013-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-013-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-013-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-013-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-013-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-013-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-013-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-014 — Canonical error envelope

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Canonical error envelope` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-014-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-014-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-014-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-014-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-014-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-014-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-014-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-014-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-014-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-014-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-014-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-014-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-014-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-014-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-014-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-014-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-014-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-014-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-014-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-014-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-014-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-014-22** — Produce a normative design subsection specific to **Canonical error envelope** with valid and invalid worked examples.
- [ ] **MC-014-23** — Create an end-to-end integration fixture proving **Canonical error envelope** works through its real production-facing path.
- [ ] **MC-014-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Canonical error envelope** and enforce them automatically.
- [ ] **MC-014-25** — Record assumptions and unsupported cases for **Canonical error envelope** in machine-readable release metadata where practical.
- [ ] **MC-014-26** — Create at least one failure-injection scenario for **Canonical error envelope** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-014-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-014-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-014-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-014-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-014-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-014-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-014-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-014-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-014-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-014-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-014-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-014-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-014-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-014-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-014-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-014-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-014-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-014-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-014-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-014-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-014-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-014-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-014-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-014-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-014-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-014-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-014-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-014-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-014-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-014-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-014-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-014-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-014-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-014-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-014-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-015 — ABI/version negotiation

**Category:** ABI Semantics  
**Implementation intent:** Deliver `ABI/version negotiation` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-015-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-015-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-015-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-015-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-015-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-015-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-015-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-015-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-015-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-015-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-015-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-015-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-015-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-015-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-015-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-015-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-015-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-015-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-015-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-015-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-015-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-015-22** — Produce a normative design subsection specific to **ABI/version negotiation** with valid and invalid worked examples.
- [ ] **MC-015-23** — Create an end-to-end integration fixture proving **ABI/version negotiation** works through its real production-facing path.
- [ ] **MC-015-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **ABI/version negotiation** and enforce them automatically.
- [ ] **MC-015-25** — Record assumptions and unsupported cases for **ABI/version negotiation** in machine-readable release metadata where practical.
- [ ] **MC-015-26** — Create at least one failure-injection scenario for **ABI/version negotiation** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-015-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-015-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-015-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-015-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-015-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-015-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-015-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-015-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-015-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-015-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-015-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-015-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-015-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-015-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-015-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-015-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-015-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-015-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-015-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-015-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-015-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-015-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-015-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-015-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-015-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-015-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-015-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-015-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-015-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-015-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-015-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-015-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-015-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-015-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-015-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-016 — Compatibility/evolution engine

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Compatibility/evolution engine` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-016-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-016-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-016-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-016-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-016-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-016-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-016-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-016-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-016-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-016-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-016-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-016-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-016-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-016-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-016-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-016-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-016-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-016-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-016-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-016-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-016-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-016-22** — Produce a normative design subsection specific to **Compatibility/evolution engine** with valid and invalid worked examples.
- [ ] **MC-016-23** — Create an end-to-end integration fixture proving **Compatibility/evolution engine** works through its real production-facing path.
- [ ] **MC-016-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Compatibility/evolution engine** and enforce them automatically.
- [ ] **MC-016-25** — Record assumptions and unsupported cases for **Compatibility/evolution engine** in machine-readable release metadata where practical.
- [ ] **MC-016-26** — Create at least one failure-injection scenario for **Compatibility/evolution engine** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-016-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-016-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-016-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-016-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-016-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-016-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-016-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-016-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-016-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-016-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-016-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-016-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-016-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-016-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-016-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-016-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-016-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-016-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-016-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-016-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-016-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-016-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-016-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-016-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-016-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-016-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-016-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-016-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-016-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-016-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-016-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-016-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-016-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-016-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-016-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-017 — Async/future/stream boundary semantics

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Async/future/stream boundary semantics` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-017-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-017-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-017-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-017-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-017-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-017-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-017-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-017-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-017-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-017-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-017-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-017-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-017-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-017-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.
- [ ] **MC-017-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.
- [ ] **MC-017-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.
- [ ] **MC-017-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.
- [ ] **MC-017-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.
- [ ] **MC-017-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.
- [ ] **MC-017-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.
- [ ] **MC-017-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.

### D. Component-Specific Controls

- [ ] **MC-017-22** — Specify completion, polling/wakeup, cancellation, terminal-state, and backpressure semantics with no duplicated terminal delivery.
- [ ] **MC-017-23** — Bound buffering and outstanding work; prove cancellation cannot leak ownership or orphan resources.
- [ ] **MC-017-24** — Use deterministic scheduler tests to reproduce lost-wakeup, double-completion, and cancellation races.
- [ ] **MC-017-25** — Produce a normative design subsection specific to **Async/future/stream boundary semantics** with valid and invalid worked examples.
- [ ] **MC-017-26** — Create an end-to-end integration fixture proving **Async/future/stream boundary semantics** works through its real production-facing path.

### E. Implementation

- [ ] **MC-017-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-017-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-017-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-017-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-017-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-017-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-017-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-017-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-017-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-017-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-017-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-017-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-017-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-017-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-017-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-017-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-017-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-017-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-017-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-017-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-017-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-017-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-017-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-017-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-017-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-017-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-017-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-017-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-017-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-017-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-017-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-017-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-017-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-017-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-017-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-018 — Schema-derived resource limits

**Category:** Security & Policy  
**Implementation intent:** Deliver `Schema-derived resource limits` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-018-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-018-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-018-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-018-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-018-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-018-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-018-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-018-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-018-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-018-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-018-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-018-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-018-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-018-14** — Document the trust boundary and exact authority granted to this component.
- [ ] **MC-018-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.
- [ ] **MC-018-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.
- [ ] **MC-018-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.
- [ ] **MC-018-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.
- [ ] **MC-018-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.
- [ ] **MC-018-20** — Classify and redact logs, errors, traces, and audit events before emission.
- [ ] **MC-018-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.

### D. Component-Specific Controls

- [ ] **MC-018-22** — Define a formal grammar or schema meta-model with source-location preservation and deterministic normalization.
- [ ] **MC-018-23** — Reject duplicate/ambiguous declarations, illegal recursion, unresolved references, and version-incompatible imports.
- [ ] **MC-018-24** — Guarantee parse → normalize → serialize determinism with golden fixtures and stable canonical hashes.
- [ ] **MC-018-25** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.
- [ ] **MC-018-26** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.

### E. Implementation

- [ ] **MC-018-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-018-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-018-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-018-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-018-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-018-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-018-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-018-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-018-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-018-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-018-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-018-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-018-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-018-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-018-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-018-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-018-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-018-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-018-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-018-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-018-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-018-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-018-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-018-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-018-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-018-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-018-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-018-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-018-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-018-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-018-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-018-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-018-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-018-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-018-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-019 — WebAssembly Component Model runtime adapter

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `WebAssembly Component Model runtime adapter` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-019-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-019-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-019-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-019-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-019-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-019-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-019-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-019-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-019-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-019-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-019-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-019-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-019-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-019-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-019-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-019-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-019-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-019-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-019-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-019-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-019-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-019-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-019-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-019-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-019-25** — Produce a normative design subsection specific to **WebAssembly Component Model runtime adapter** with valid and invalid worked examples.
- [ ] **MC-019-26** — Create an end-to-end integration fixture proving **WebAssembly Component Model runtime adapter** works through its real production-facing path.

### E. Implementation

- [ ] **MC-019-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-019-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-019-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-019-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-019-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-019-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-019-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-019-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-019-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-019-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-019-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-019-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-019-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-019-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-019-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-019-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-019-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-019-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-019-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-019-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-019-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-019-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-019-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-019-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-019-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-019-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-019-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-019-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-019-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-019-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-019-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-019-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-019-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-019-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-019-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-020 — Rust binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Rust binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-020-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-020-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-020-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-020-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-020-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-020-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-020-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-020-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-020-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-020-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-020-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-020-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-020-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-020-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-020-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-020-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-020-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-020-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-020-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-020-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-020-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-020-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-020-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-020-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-020-25** — Produce a normative design subsection specific to **Rust binding adapter and fixture component** with valid and invalid worked examples.
- [ ] **MC-020-26** — Create an end-to-end integration fixture proving **Rust binding adapter and fixture component** works through its real production-facing path.

### E. Implementation

- [ ] **MC-020-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-020-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-020-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-020-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-020-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-020-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-020-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-020-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-020-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-020-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-020-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-020-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-020-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-020-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-020-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-020-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-020-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-020-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-020-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-020-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-020-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-020-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-020-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-020-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-020-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-020-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-020-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-020-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-020-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-020-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-020-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-020-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-020-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-020-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-020-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-021 — Go binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Go binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-021-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-021-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-021-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-021-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-021-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-021-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-021-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-021-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-021-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-021-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-021-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-021-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-021-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-021-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-021-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-021-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-021-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-021-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-021-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-021-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-021-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-021-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-021-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-021-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-021-25** — Produce a normative design subsection specific to **Go binding adapter and fixture component** with valid and invalid worked examples.
- [ ] **MC-021-26** — Create an end-to-end integration fixture proving **Go binding adapter and fixture component** works through its real production-facing path.

### E. Implementation

- [ ] **MC-021-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-021-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-021-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-021-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-021-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-021-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-021-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-021-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-021-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-021-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-021-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-021-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-021-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-021-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-021-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-021-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-021-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-021-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-021-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-021-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-021-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-021-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-021-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-021-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-021-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-021-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-021-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-021-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-021-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-021-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-021-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-021-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-021-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-021-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-021-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-022 — JavaScript binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `JavaScript binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-022-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-022-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-022-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-022-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-022-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-022-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-022-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-022-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-022-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-022-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-022-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-022-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-022-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-022-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-022-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-022-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-022-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-022-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-022-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-022-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-022-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-022-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-022-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-022-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-022-25** — Produce a normative design subsection specific to **JavaScript binding adapter and fixture component** with valid and invalid worked examples.
- [ ] **MC-022-26** — Create an end-to-end integration fixture proving **JavaScript binding adapter and fixture component** works through its real production-facing path.

### E. Implementation

- [ ] **MC-022-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-022-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-022-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-022-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-022-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-022-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-022-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-022-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-022-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-022-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-022-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-022-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-022-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-022-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-022-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-022-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-022-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-022-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-022-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-022-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-022-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-022-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-022-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-022-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-022-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-022-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-022-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-022-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-022-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-022-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-022-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-022-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-022-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-022-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-022-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-023 — Python binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Python binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-023-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-023-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-023-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-023-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-023-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-023-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-023-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-023-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-023-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-023-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-023-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-023-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-023-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-023-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.
- [ ] **MC-023-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.
- [ ] **MC-023-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.
- [ ] **MC-023-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.
- [ ] **MC-023-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.
- [ ] **MC-023-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.
- [ ] **MC-023-20** — Provide a fixture component/module that exercises the complete supported type surface.
- [ ] **MC-023-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.

### D. Component-Specific Controls

- [ ] **MC-023-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-023-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-023-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-023-25** — Produce a normative design subsection specific to **Python binding adapter and fixture component** with valid and invalid worked examples.
- [ ] **MC-023-26** — Create an end-to-end integration fixture proving **Python binding adapter and fixture component** works through its real production-facing path.

### E. Implementation

- [ ] **MC-023-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-023-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-023-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-023-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-023-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-023-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-023-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-023-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-023-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-023-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-023-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-023-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-023-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-023-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-023-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-023-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-023-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-023-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-023-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-023-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-023-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-023-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-023-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-023-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-023-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-023-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-023-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-023-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-023-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-023-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-023-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-023-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-023-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-023-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-023-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-024 — Cross-language conformance matrix

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Cross-language conformance matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-024-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-024-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-024-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-024-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-024-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-024-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-024-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-024-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-024-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-024-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-024-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-024-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-024-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-024-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-024-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-024-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-024-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-024-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-024-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-024-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-024-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-024-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-024-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-024-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-024-25** — Produce a normative design subsection specific to **Cross-language conformance matrix** with valid and invalid worked examples.
- [ ] **MC-024-26** — Create an end-to-end integration fixture proving **Cross-language conformance matrix** works through its real production-facing path.

### E. Implementation

- [ ] **MC-024-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-024-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-024-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-024-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-024-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-024-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-024-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-024-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-024-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-024-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-024-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-024-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-024-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-024-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-024-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-024-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-024-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-024-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-024-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-024-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-024-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-024-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-024-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-024-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-024-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-024-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-024-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-024-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-024-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-024-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-024-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-024-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-024-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-024-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-024-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-025 — Adjacent-layer integration fixtures

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Adjacent-layer integration fixtures` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-025-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-025-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-025-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-025-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-025-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-025-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-025-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-025-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-025-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-025-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-025-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-025-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-025-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-025-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-025-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-025-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-025-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-025-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-025-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-025-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-025-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-025-22** — Produce a normative design subsection specific to **Adjacent-layer integration fixtures** with valid and invalid worked examples.
- [ ] **MC-025-23** — Create an end-to-end integration fixture proving **Adjacent-layer integration fixtures** works through its real production-facing path.
- [ ] **MC-025-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Adjacent-layer integration fixtures** and enforce them automatically.
- [ ] **MC-025-25** — Record assumptions and unsupported cases for **Adjacent-layer integration fixtures** in machine-readable release metadata where practical.
- [ ] **MC-025-26** — Create at least one failure-injection scenario for **Adjacent-layer integration fixtures** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-025-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-025-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-025-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-025-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-025-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-025-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-025-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-025-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-025-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-025-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-025-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-025-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-025-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-025-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-025-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-025-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-025-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-025-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-025-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-025-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-025-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-025-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-025-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-025-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-025-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-025-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-025-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-025-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-025-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-025-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-025-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-025-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-025-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-025-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-025-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-026 — Golden canonical test-vector corpus

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Golden canonical test-vector corpus` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-026-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-026-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-026-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-026-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-026-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-026-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-026-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-026-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-026-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-026-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-026-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-026-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-026-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-026-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-026-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-026-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-026-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-026-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-026-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-026-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-026-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-026-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-026-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-026-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-026-25** — Produce a normative design subsection specific to **Golden canonical test-vector corpus** with valid and invalid worked examples.
- [ ] **MC-026-26** — Create an end-to-end integration fixture proving **Golden canonical test-vector corpus** works through its real production-facing path.

### E. Implementation

- [ ] **MC-026-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-026-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-026-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-026-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-026-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-026-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-026-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-026-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-026-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-026-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-026-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-026-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-026-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-026-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-026-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-026-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-026-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-026-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-026-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-026-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-026-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-026-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-026-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-026-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-026-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-026-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-026-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-026-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-026-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-026-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-026-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-026-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-026-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-026-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-026-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-027 — Property-based test harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Property-based test harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-027-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-027-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-027-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-027-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-027-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-027-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-027-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-027-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-027-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-027-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-027-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-027-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-027-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-027-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-027-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-027-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-027-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-027-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-027-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-027-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-027-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-027-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-027-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-027-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-027-25** — Produce a normative design subsection specific to **Property-based test harness** with valid and invalid worked examples.
- [ ] **MC-027-26** — Create an end-to-end integration fixture proving **Property-based test harness** works through its real production-facing path.

### E. Implementation

- [ ] **MC-027-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-027-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-027-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-027-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-027-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-027-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-027-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-027-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-027-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-027-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-027-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-027-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-027-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-027-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-027-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-027-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-027-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-027-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-027-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-027-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-027-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-027-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-027-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-027-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-027-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-027-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-027-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-027-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-027-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-027-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-027-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-027-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-027-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-027-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-027-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-028 — Coverage-guided fuzzing harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Coverage-guided fuzzing harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-028-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-028-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-028-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-028-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-028-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-028-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-028-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-028-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-028-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-028-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-028-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-028-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-028-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-028-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-028-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-028-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-028-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-028-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-028-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-028-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-028-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-028-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-028-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-028-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-028-25** — Produce a normative design subsection specific to **Coverage-guided fuzzing harness** with valid and invalid worked examples.
- [ ] **MC-028-26** — Create an end-to-end integration fixture proving **Coverage-guided fuzzing harness** works through its real production-facing path.

### E. Implementation

- [ ] **MC-028-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-028-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-028-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-028-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-028-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-028-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-028-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-028-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-028-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-028-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-028-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-028-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-028-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-028-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-028-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-028-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-028-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-028-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-028-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-028-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-028-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-028-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-028-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-028-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-028-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-028-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-028-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-028-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-028-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-028-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-028-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-028-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-028-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-028-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-028-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-029 — Differential runtime tester

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Differential runtime tester` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-029-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-029-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-029-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-029-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-029-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-029-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-029-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-029-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-029-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-029-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-029-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-029-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-029-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-029-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-029-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-029-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-029-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-029-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-029-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-029-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-029-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-029-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-029-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-029-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-029-25** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-029-26** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.

### E. Implementation

- [ ] **MC-029-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-029-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-029-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-029-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-029-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-029-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-029-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-029-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-029-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-029-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-029-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-029-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-029-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-029-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-029-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-029-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-029-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-029-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-029-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-029-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-029-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-029-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-029-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-029-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-029-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-029-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-029-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-029-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-029-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-029-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-029-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-029-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-029-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-029-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-029-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-030 — Malicious-memory test harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Malicious-memory test harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-030-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-030-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-030-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-030-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-030-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-030-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-030-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-030-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-030-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-030-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-030-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-030-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-030-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-030-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-030-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-030-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-030-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-030-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-030-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-030-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-030-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-030-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.
- [ ] **MC-030-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.
- [ ] **MC-030-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.
- [ ] **MC-030-25** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-030-26** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.

### E. Implementation

- [ ] **MC-030-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-030-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-030-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-030-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-030-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-030-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-030-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-030-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-030-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-030-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-030-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-030-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-030-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-030-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-030-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-030-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-030-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-030-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-030-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-030-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-030-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-030-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-030-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-030-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-030-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-030-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-030-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-030-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-030-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-030-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-030-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-030-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-030-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-030-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-030-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-031 — Concurrency/race stress suite

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Concurrency/race stress suite` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-031-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-031-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-031-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-031-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-031-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-031-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-031-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-031-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-031-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-031-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-031-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-031-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-031-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-031-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-031-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-031-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-031-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-031-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-031-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-031-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-031-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-031-22** — Produce a normative design subsection specific to **Concurrency/race stress suite** with valid and invalid worked examples.
- [ ] **MC-031-23** — Create an end-to-end integration fixture proving **Concurrency/race stress suite** works through its real production-facing path.
- [ ] **MC-031-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Concurrency/race stress suite** and enforce them automatically.
- [ ] **MC-031-25** — Record assumptions and unsupported cases for **Concurrency/race stress suite** in machine-readable release metadata where practical.
- [ ] **MC-031-26** — Create at least one failure-injection scenario for **Concurrency/race stress suite** that proves safe rollback or containment.

### E. Implementation

- [ ] **MC-031-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-031-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-031-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-031-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-031-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-031-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-031-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-031-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-031-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-031-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-031-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-031-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-031-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-031-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-031-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-031-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-031-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-031-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-031-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-031-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-031-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-031-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-031-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-031-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-031-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-031-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-031-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-031-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-031-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-031-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-031-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-031-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-031-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-031-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-031-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-032 — Leak/use-after-free detector integration

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Leak/use-after-free detector integration` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-032-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-032-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-032-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-032-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-032-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-032-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-032-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-032-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-032-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-032-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-032-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-032-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-032-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-032-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-032-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-032-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-032-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-032-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-032-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-032-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-032-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-032-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-032-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-032-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-032-25** — Produce a normative design subsection specific to **Leak/use-after-free detector integration** with valid and invalid worked examples.
- [ ] **MC-032-26** — Create an end-to-end integration fixture proving **Leak/use-after-free detector integration** works through its real production-facing path.

### E. Implementation

- [ ] **MC-032-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-032-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-032-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-032-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-032-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-032-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-032-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-032-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-032-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-032-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-032-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-032-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-032-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-032-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-032-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-032-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-032-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-032-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-032-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-032-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-032-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-032-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-032-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-032-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-032-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-032-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-032-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-032-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-032-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-032-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-032-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-032-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-032-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-032-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-032-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-033 — Cross-platform architecture matrix

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Cross-platform architecture matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-033-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-033-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-033-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-033-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-033-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-033-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-033-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-033-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-033-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-033-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-033-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-033-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-033-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-033-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-033-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-033-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-033-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-033-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-033-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-033-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-033-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-033-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-033-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-033-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-033-25** — Produce a normative design subsection specific to **Cross-platform architecture matrix** with valid and invalid worked examples.
- [ ] **MC-033-26** — Create an end-to-end integration fixture proving **Cross-platform architecture matrix** works through its real production-facing path.

### E. Implementation

- [ ] **MC-033-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-033-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-033-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-033-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-033-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-033-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-033-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-033-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-033-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-033-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-033-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-033-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-033-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-033-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-033-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-033-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-033-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-033-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-033-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-033-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-033-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-033-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-033-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-033-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-033-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-033-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-033-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-033-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-033-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-033-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-033-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-033-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-033-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-033-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-033-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-034 — Performance benchmark harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Performance benchmark harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-034-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-034-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-034-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-034-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-034-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-034-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-034-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-034-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-034-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-034-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-034-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-034-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-034-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-034-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-034-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-034-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-034-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-034-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-034-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-034-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-034-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-034-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-034-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-034-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-034-25** — Produce a normative design subsection specific to **Performance benchmark harness** with valid and invalid worked examples.
- [ ] **MC-034-26** — Create an end-to-end integration fixture proving **Performance benchmark harness** works through its real production-facing path.

### E. Implementation

- [ ] **MC-034-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-034-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-034-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-034-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-034-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-034-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-034-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-034-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-034-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-034-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-034-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-034-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-034-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-034-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-034-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-034-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-034-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-034-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-034-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-034-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-034-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-034-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-034-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-034-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-034-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-034-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-034-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-034-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-034-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-034-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-034-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-034-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-034-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-034-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-034-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-035 — SLO certification gate

**Category:** Verification & Certification  
**Implementation intent:** Deliver `SLO certification gate` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-035-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-035-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-035-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-035-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-035-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-035-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-035-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-035-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-035-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-035-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-035-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-035-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-035-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-035-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-035-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-035-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-035-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-035-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-035-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-035-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-035-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-035-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-035-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-035-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-035-25** — Produce a normative design subsection specific to **SLO certification gate** with valid and invalid worked examples.
- [ ] **MC-035-26** — Create an end-to-end integration fixture proving **SLO certification gate** works through its real production-facing path.

### E. Implementation

- [ ] **MC-035-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-035-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-035-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-035-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-035-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-035-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-035-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-035-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-035-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-035-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-035-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-035-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-035-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-035-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-035-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-035-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-035-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-035-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-035-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-035-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-035-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-035-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-035-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-035-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-035-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-035-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-035-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-035-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-035-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-035-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-035-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-035-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-035-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-035-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-035-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-036 — Large-payload/DoS benchmark suite

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Large-payload/DoS benchmark suite` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-036-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-036-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-036-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-036-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-036-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-036-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-036-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-036-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-036-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-036-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-036-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-036-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-036-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-036-14** — Keep the reference oracle independent from the implementation under test.
- [ ] **MC-036-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.
- [ ] **MC-036-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.
- [ ] **MC-036-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.
- [ ] **MC-036-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.
- [ ] **MC-036-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.
- [ ] **MC-036-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.
- [ ] **MC-036-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.

### D. Component-Specific Controls

- [ ] **MC-036-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-036-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-036-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-036-25** — Produce a normative design subsection specific to **Large-payload/DoS benchmark suite** with valid and invalid worked examples.
- [ ] **MC-036-26** — Create an end-to-end integration fixture proving **Large-payload/DoS benchmark suite** works through its real production-facing path.

### E. Implementation

- [ ] **MC-036-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-036-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-036-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-036-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-036-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-036-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-036-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-036-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-036-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-036-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-036-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-036-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-036-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-036-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-036-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-036-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-036-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-036-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-036-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-036-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-036-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-036-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-036-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-036-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-036-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-036-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-036-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-036-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-036-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-036-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-036-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-036-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-036-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-036-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-036-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-037 — Metrics emitter

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Metrics emitter` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-037-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-037-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-037-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-037-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-037-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-037-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-037-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-037-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-037-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-037-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-037-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-037-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-037-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-037-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.
- [ ] **MC-037-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.
- [ ] **MC-037-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.
- [ ] **MC-037-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.
- [ ] **MC-037-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.
- [ ] **MC-037-19** — Provide runbook queries or dashboards mapped directly to component failure modes.
- [ ] **MC-037-20** — Version telemetry schemas and preserve compatibility for downstream automation.
- [ ] **MC-037-21** — Exercise observability in integration tests so critical failures cannot occur silently.

### D. Component-Specific Controls

- [ ] **MC-037-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.
- [ ] **MC-037-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.
- [ ] **MC-037-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.
- [ ] **MC-037-25** — Produce a normative design subsection specific to **Metrics emitter** with valid and invalid worked examples.
- [ ] **MC-037-26** — Create an end-to-end integration fixture proving **Metrics emitter** works through its real production-facing path.

### E. Implementation

- [ ] **MC-037-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-037-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-037-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-037-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-037-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-037-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-037-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-037-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-037-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-037-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-037-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-037-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-037-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-037-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-037-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-037-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-037-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-037-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-037-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-037-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-037-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-037-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-037-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-037-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-037-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-037-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-037-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-037-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-037-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-037-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-037-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-037-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-037-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-037-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-037-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-038 — Distributed trace instrumentation

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Distributed trace instrumentation` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-038-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-038-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-038-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-038-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-038-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-038-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-038-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-038-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-038-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-038-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-038-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-038-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-038-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-038-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.
- [ ] **MC-038-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.
- [ ] **MC-038-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.
- [ ] **MC-038-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.
- [ ] **MC-038-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.
- [ ] **MC-038-19** — Provide runbook queries or dashboards mapped directly to component failure modes.
- [ ] **MC-038-20** — Version telemetry schemas and preserve compatibility for downstream automation.
- [ ] **MC-038-21** — Exercise observability in integration tests so critical failures cannot occur silently.

### D. Component-Specific Controls

- [ ] **MC-038-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.
- [ ] **MC-038-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.
- [ ] **MC-038-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.
- [ ] **MC-038-25** — Produce a normative design subsection specific to **Distributed trace instrumentation** with valid and invalid worked examples.
- [ ] **MC-038-26** — Create an end-to-end integration fixture proving **Distributed trace instrumentation** works through its real production-facing path.

### E. Implementation

- [ ] **MC-038-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-038-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-038-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-038-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-038-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-038-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-038-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-038-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-038-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-038-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-038-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-038-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-038-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-038-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-038-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-038-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-038-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-038-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-038-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-038-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-038-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-038-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-038-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-038-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-038-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-038-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-038-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-038-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-038-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-038-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-038-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-038-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-038-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-038-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-038-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-039 — Structured security audit events

**Category:** Security & Policy  
**Implementation intent:** Deliver `Structured security audit events` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-039-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-039-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-039-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-039-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-039-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-039-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-039-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-039-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-039-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-039-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-039-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-039-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-039-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-039-14** — Document the trust boundary and exact authority granted to this component.
- [ ] **MC-039-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.
- [ ] **MC-039-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.
- [ ] **MC-039-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.
- [ ] **MC-039-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.
- [ ] **MC-039-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.
- [ ] **MC-039-20** — Classify and redact logs, errors, traces, and audit events before emission.
- [ ] **MC-039-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.

### D. Component-Specific Controls

- [ ] **MC-039-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.
- [ ] **MC-039-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.
- [ ] **MC-039-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.
- [ ] **MC-039-25** — Produce a normative design subsection specific to **Structured security audit events** with valid and invalid worked examples.
- [ ] **MC-039-26** — Create an end-to-end integration fixture proving **Structured security audit events** works through its real production-facing path.

### E. Implementation

- [ ] **MC-039-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-039-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-039-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-039-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-039-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-039-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-039-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-039-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-039-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-039-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-039-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-039-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-039-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-039-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-039-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-039-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-039-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-039-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-039-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-039-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-039-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-039-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-039-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-039-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-039-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-039-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-039-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-039-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-039-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-039-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-039-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-039-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-039-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-039-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-039-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-040 — Diagnostic redaction policy

**Category:** Security & Policy  
**Implementation intent:** Deliver `Diagnostic redaction policy` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-040-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-040-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-040-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-040-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-040-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-040-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-040-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-040-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-040-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-040-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-040-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-040-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-040-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-040-14** — Document the trust boundary and exact authority granted to this component.
- [ ] **MC-040-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.
- [ ] **MC-040-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.
- [ ] **MC-040-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.
- [ ] **MC-040-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.
- [ ] **MC-040-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.
- [ ] **MC-040-20** — Classify and redact logs, errors, traces, and audit events before emission.
- [ ] **MC-040-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.

### D. Component-Specific Controls

- [ ] **MC-040-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.
- [ ] **MC-040-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.
- [ ] **MC-040-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.
- [ ] **MC-040-25** — Produce a normative design subsection specific to **Diagnostic redaction policy** with valid and invalid worked examples.
- [ ] **MC-040-26** — Create an end-to-end integration fixture proving **Diagnostic redaction policy** works through its real production-facing path.

### E. Implementation

- [ ] **MC-040-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-040-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-040-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-040-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-040-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-040-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-040-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-040-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-040-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-040-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-040-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-040-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-040-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-040-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-040-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-040-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-040-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-040-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-040-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-040-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-040-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-040-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-040-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-040-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-040-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-040-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-040-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-040-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-040-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-040-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-040-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-040-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-040-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-040-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-040-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-041 — Runtime health/readiness model

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Runtime health/readiness model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-041-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-041-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-041-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-041-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-041-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-041-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-041-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-041-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-041-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-041-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-041-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-041-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-041-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-041-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.
- [ ] **MC-041-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.
- [ ] **MC-041-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.
- [ ] **MC-041-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.
- [ ] **MC-041-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.
- [ ] **MC-041-19** — Provide runbook queries or dashboards mapped directly to component failure modes.
- [ ] **MC-041-20** — Version telemetry schemas and preserve compatibility for downstream automation.
- [ ] **MC-041-21** — Exercise observability in integration tests so critical failures cannot occur silently.

### D. Component-Specific Controls

- [ ] **MC-041-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.
- [ ] **MC-041-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.
- [ ] **MC-041-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.
- [ ] **MC-041-25** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.
- [ ] **MC-041-26** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.

### E. Implementation

- [ ] **MC-041-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-041-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-041-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-041-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-041-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-041-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-041-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-041-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-041-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-041-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-041-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-041-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-041-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-041-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-041-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-041-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-041-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-041-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-041-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-041-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-041-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-041-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-041-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-041-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-041-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-041-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-041-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-041-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-041-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-041-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-041-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-041-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-041-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-041-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-041-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-042 — Capacity/fairness controller

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Capacity/fairness controller` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-042-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-042-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-042-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-042-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-042-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-042-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-042-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-042-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-042-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-042-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-042-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-042-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-042-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-042-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.
- [ ] **MC-042-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.
- [ ] **MC-042-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.
- [ ] **MC-042-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.
- [ ] **MC-042-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.
- [ ] **MC-042-19** — Provide runbook queries or dashboards mapped directly to component failure modes.
- [ ] **MC-042-20** — Version telemetry schemas and preserve compatibility for downstream automation.
- [ ] **MC-042-21** — Exercise observability in integration tests so critical failures cannot occur silently.

### D. Component-Specific Controls

- [ ] **MC-042-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.
- [ ] **MC-042-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.
- [ ] **MC-042-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.
- [ ] **MC-042-25** — Produce a normative design subsection specific to **Capacity/fairness controller** with valid and invalid worked examples.
- [ ] **MC-042-26** — Create an end-to-end integration fixture proving **Capacity/fairness controller** works through its real production-facing path.

### E. Implementation

- [ ] **MC-042-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-042-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-042-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-042-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-042-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-042-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-042-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-042-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-042-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-042-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-042-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-042-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-042-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-042-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-042-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-042-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-042-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-042-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-042-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-042-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-042-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-042-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-042-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-042-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-042-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-042-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-042-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-042-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-042-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-042-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-042-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-042-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-042-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-042-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-042-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-043 — Declarative configuration schema

**Category:** Configuration & Governance  
**Implementation intent:** Deliver `Declarative configuration schema` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-043-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-043-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-043-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-043-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-043-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-043-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-043-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-043-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-043-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-043-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-043-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-043-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-043-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-043-14** — Define a versioned machine-readable schema with defaults, constraints, deprecations, and required fields.
- [ ] **MC-043-15** — Reject unknown or malformed critical settings unless explicitly declared forward-compatible.
- [ ] **MC-043-16** — Validate the full candidate configuration before mutating live state.
- [ ] **MC-043-17** — Support atomic commit/rollback and retain previous known-good configuration metadata.
- [ ] **MC-043-18** — Record actor/source, before/after digests, timestamps, and resulting effective version for each change.
- [ ] **MC-043-19** — Separate secret references from ordinary configuration values.
- [ ] **MC-043-20** — Test mixed-version, partial-deployment, downgrade, and rollback behavior.
- [ ] **MC-043-21** — Generate human-readable configuration documentation from the canonical schema.

### D. Component-Specific Controls

- [ ] **MC-043-22** — Define a formal grammar or schema meta-model with source-location preservation and deterministic normalization.
- [ ] **MC-043-23** — Reject duplicate/ambiguous declarations, illegal recursion, unresolved references, and version-incompatible imports.
- [ ] **MC-043-24** — Guarantee parse → normalize → serialize determinism with golden fixtures and stable canonical hashes.
- [ ] **MC-043-25** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.
- [ ] **MC-043-26** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.

### E. Implementation

- [ ] **MC-043-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-043-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-043-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-043-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-043-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-043-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-043-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-043-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-043-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-043-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-043-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-043-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-043-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-043-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-043-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-043-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-043-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-043-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-043-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-043-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-043-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-043-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-043-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-043-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-043-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-043-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-043-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-043-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-043-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-043-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-043-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-043-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-043-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-043-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-043-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-044 — Configuration validator/transaction manager

**Category:** Configuration & Governance  
**Implementation intent:** Deliver `Configuration validator/transaction manager` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-044-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-044-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-044-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-044-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-044-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-044-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-044-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-044-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-044-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-044-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-044-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-044-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-044-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-044-14** — Define a versioned machine-readable schema with defaults, constraints, deprecations, and required fields.
- [ ] **MC-044-15** — Reject unknown or malformed critical settings unless explicitly declared forward-compatible.
- [ ] **MC-044-16** — Validate the full candidate configuration before mutating live state.
- [ ] **MC-044-17** — Support atomic commit/rollback and retain previous known-good configuration metadata.
- [ ] **MC-044-18** — Record actor/source, before/after digests, timestamps, and resulting effective version for each change.
- [ ] **MC-044-19** — Separate secret references from ordinary configuration values.
- [ ] **MC-044-20** — Test mixed-version, partial-deployment, downgrade, and rollback behavior.
- [ ] **MC-044-21** — Generate human-readable configuration documentation from the canonical schema.

### D. Component-Specific Controls

- [ ] **MC-044-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.
- [ ] **MC-044-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.
- [ ] **MC-044-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.
- [ ] **MC-044-25** — Produce a normative design subsection specific to **Configuration validator/transaction manager** with valid and invalid worked examples.
- [ ] **MC-044-26** — Create an end-to-end integration fixture proving **Configuration validator/transaction manager** works through its real production-facing path.

### E. Implementation

- [ ] **MC-044-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-044-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-044-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-044-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-044-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-044-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-044-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-044-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-044-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-044-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-044-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-044-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-044-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-044-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-044-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-044-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-044-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-044-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-044-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-044-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-044-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-044-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-044-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-044-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-044-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-044-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-044-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-044-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-044-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-044-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-044-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-044-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-044-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-044-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-044-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-045 — Mapping-policy provenance

**Category:** Supply Chain & Trust  
**Implementation intent:** Deliver `Mapping-policy provenance` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-045-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-045-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-045-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-045-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-045-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-045-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-045-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-045-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-045-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-045-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-045-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-045-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-045-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-045-14** — Use cryptographic digests for every externally loaded artifact, policy, generated binding, and release object.
- [ ] **MC-045-15** — Verify provenance/signatures before use and fail closed when mandatory evidence is missing or invalid.
- [ ] **MC-045-16** — Pin build tools and dependencies sufficiently for reproducible or explainably non-reproducible builds.
- [ ] **MC-045-17** — Record signer identity, source revision, builder identity, dependency graph, and build environment.
- [ ] **MC-045-18** — Implement key/root rotation and revocation handling without unsafe bypasses.
- [ ] **MC-045-19** — Separate verification mechanism from policy and version both independently.
- [ ] **MC-045-20** — Continuously scan dependencies/artifacts and define remediation SLA by severity.
- [ ] **MC-045-21** — Retain verification evidence so historical releases can be independently re-evaluated.

### D. Component-Specific Controls

- [ ] **MC-045-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.
- [ ] **MC-045-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.
- [ ] **MC-045-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.
- [ ] **MC-045-25** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.
- [ ] **MC-045-26** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.

### E. Implementation

- [ ] **MC-045-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-045-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-045-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-045-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-045-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-045-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-045-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-045-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-045-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-045-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-045-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-045-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-045-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-045-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-045-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-045-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-045-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-045-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-045-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-045-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-045-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-045-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-045-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-045-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-045-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-045-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-045-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-045-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-045-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-045-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-045-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-045-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-045-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-045-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-045-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-046 — Artifact provenance verifier

**Category:** Supply Chain & Trust  
**Implementation intent:** Deliver `Artifact provenance verifier` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-046-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-046-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-046-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-046-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-046-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-046-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-046-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-046-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-046-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-046-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-046-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-046-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-046-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-046-14** — Use cryptographic digests for every externally loaded artifact, policy, generated binding, and release object.
- [ ] **MC-046-15** — Verify provenance/signatures before use and fail closed when mandatory evidence is missing or invalid.
- [ ] **MC-046-16** — Pin build tools and dependencies sufficiently for reproducible or explainably non-reproducible builds.
- [ ] **MC-046-17** — Record signer identity, source revision, builder identity, dependency graph, and build environment.
- [ ] **MC-046-18** — Implement key/root rotation and revocation handling without unsafe bypasses.
- [ ] **MC-046-19** — Separate verification mechanism from policy and version both independently.
- [ ] **MC-046-20** — Continuously scan dependencies/artifacts and define remediation SLA by severity.
- [ ] **MC-046-21** — Retain verification evidence so historical releases can be independently re-evaluated.

### D. Component-Specific Controls

- [ ] **MC-046-22** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.
- [ ] **MC-046-23** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.
- [ ] **MC-046-24** — Test substitution, replay, expiry, revocation, downgrade, and trust-service outage behavior with fail-closed defaults.
- [ ] **MC-046-25** — Produce a normative design subsection specific to **Artifact provenance verifier** with valid and invalid worked examples.
- [ ] **MC-046-26** — Create an end-to-end integration fixture proving **Artifact provenance verifier** works through its real production-facing path.

### E. Implementation

- [ ] **MC-046-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-046-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-046-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-046-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-046-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-046-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-046-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-046-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-046-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-046-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-046-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-046-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-046-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-046-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-046-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-046-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-046-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-046-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-046-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-046-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-046-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-046-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-046-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-046-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-046-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-046-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-046-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-046-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-046-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-046-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-046-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-046-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-046-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-046-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-046-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-047 — SBOM and dependency lock

**Category:** Supply Chain & Trust  
**Implementation intent:** Deliver `SBOM and dependency lock` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-047-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-047-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-047-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-047-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-047-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-047-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-047-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-047-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-047-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-047-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-047-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-047-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-047-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-047-14** — Use cryptographic digests for every externally loaded artifact, policy, generated binding, and release object.
- [ ] **MC-047-15** — Verify provenance/signatures before use and fail closed when mandatory evidence is missing or invalid.
- [ ] **MC-047-16** — Pin build tools and dependencies sufficiently for reproducible or explainably non-reproducible builds.
- [ ] **MC-047-17** — Record signer identity, source revision, builder identity, dependency graph, and build environment.
- [ ] **MC-047-18** — Implement key/root rotation and revocation handling without unsafe bypasses.
- [ ] **MC-047-19** — Separate verification mechanism from policy and version both independently.
- [ ] **MC-047-20** — Continuously scan dependencies/artifacts and define remediation SLA by severity.
- [ ] **MC-047-21** — Retain verification evidence so historical releases can be independently re-evaluated.

### D. Component-Specific Controls

- [ ] **MC-047-22** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.
- [ ] **MC-047-23** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.
- [ ] **MC-047-24** — Test substitution, replay, expiry, revocation, downgrade, and trust-service outage behavior with fail-closed defaults.
- [ ] **MC-047-25** — Produce a normative design subsection specific to **SBOM and dependency lock** with valid and invalid worked examples.
- [ ] **MC-047-26** — Create an end-to-end integration fixture proving **SBOM and dependency lock** works through its real production-facing path.

### E. Implementation

- [ ] **MC-047-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-047-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-047-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-047-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-047-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-047-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-047-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-047-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-047-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-047-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-047-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-047-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-047-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-047-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-047-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-047-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-047-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-047-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-047-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-047-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-047-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-047-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-047-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-047-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-047-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-047-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-047-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-047-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-047-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-047-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-047-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-047-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-047-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-047-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-047-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-048 — Capability/authentication integration

**Category:** Security & Policy  
**Implementation intent:** Deliver `Capability/authentication integration` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-048-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-048-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-048-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-048-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-048-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-048-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-048-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-048-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-048-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-048-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-048-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-048-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-048-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-048-14** — Document the trust boundary and exact authority granted to this component.
- [ ] **MC-048-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.
- [ ] **MC-048-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.
- [ ] **MC-048-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.
- [ ] **MC-048-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.
- [ ] **MC-048-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.
- [ ] **MC-048-20** — Classify and redact logs, errors, traces, and audit events before emission.
- [ ] **MC-048-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.

### D. Component-Specific Controls

- [ ] **MC-048-22** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.
- [ ] **MC-048-23** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.
- [ ] **MC-048-24** — Test substitution, replay, expiry, revocation, downgrade, and trust-service outage behavior with fail-closed defaults.
- [ ] **MC-048-25** — Produce a normative design subsection specific to **Capability/authentication integration** with valid and invalid worked examples.
- [ ] **MC-048-26** — Create an end-to-end integration fixture proving **Capability/authentication integration** works through its real production-facing path.

### E. Implementation

- [ ] **MC-048-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-048-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-048-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-048-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-048-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-048-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-048-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-048-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-048-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-048-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-048-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-048-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-048-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-048-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-048-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-048-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-048-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-048-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-048-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-048-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-048-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-048-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-048-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-048-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-048-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-048-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-048-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-048-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-048-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-048-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-048-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-048-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-048-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-048-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-048-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-049 — Trust-service outage policy

**Category:** Security & Policy  
**Implementation intent:** Deliver `Trust-service outage policy` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-049-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-049-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-049-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-049-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-049-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-049-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-049-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-049-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-049-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-049-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-049-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-049-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-049-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-049-14** — Document the trust boundary and exact authority granted to this component.
- [ ] **MC-049-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.
- [ ] **MC-049-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.
- [ ] **MC-049-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.
- [ ] **MC-049-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.
- [ ] **MC-049-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.
- [ ] **MC-049-20** — Classify and redact logs, errors, traces, and audit events before emission.
- [ ] **MC-049-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.

### D. Component-Specific Controls

- [ ] **MC-049-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.
- [ ] **MC-049-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.
- [ ] **MC-049-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.
- [ ] **MC-049-25** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.
- [ ] **MC-049-26** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.

### E. Implementation

- [ ] **MC-049-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-049-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-049-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-049-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-049-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-049-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-049-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-049-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-049-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-049-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-049-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-049-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-049-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-049-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-049-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-049-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-049-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-049-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-049-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-049-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-049-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-049-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-049-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-049-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-049-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-049-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-049-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-049-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-049-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-049-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-049-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-049-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-049-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-049-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-049-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-050 — Architecture Decision Record

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Architecture Decision Record` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-050-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-050-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-050-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-050-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-050-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-050-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-050-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-050-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-050-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-050-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-050-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-050-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-050-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-050-14** — Assign a durable owner, reviewers, and review cadence.
- [ ] **MC-050-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.
- [ ] **MC-050-16** — Record assumptions and distinguish verified facts from design intent and deferred work.
- [ ] **MC-050-17** — Require architecture/security review for changes affecting semantics or trust boundaries.
- [ ] **MC-050-18** — Version document/evidence schemas and preserve immutable historical copies.
- [ ] **MC-050-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.
- [ ] **MC-050-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.
- [ ] **MC-050-21** — Make release approval depend on evidence completeness rather than document existence.

### D. Component-Specific Controls

- [ ] **MC-050-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.
- [ ] **MC-050-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.
- [ ] **MC-050-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.
- [ ] **MC-050-25** — Produce a normative design subsection specific to **Architecture Decision Record** with valid and invalid worked examples.
- [ ] **MC-050-26** — Create an end-to-end integration fixture proving **Architecture Decision Record** works through its real production-facing path.

### E. Implementation

- [ ] **MC-050-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-050-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-050-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-050-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-050-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-050-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-050-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-050-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-050-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-050-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-050-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-050-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-050-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-050-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-050-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-050-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-050-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-050-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-050-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-050-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-050-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-050-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-050-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-050-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-050-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-050-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-050-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-050-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-050-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-050-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-050-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-050-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-050-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-050-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-050-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-051 — Formal threat model

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Formal threat model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-051-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-051-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-051-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-051-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-051-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-051-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-051-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-051-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-051-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-051-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-051-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-051-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-051-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-051-14** — Assign a durable owner, reviewers, and review cadence.
- [ ] **MC-051-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.
- [ ] **MC-051-16** — Record assumptions and distinguish verified facts from design intent and deferred work.
- [ ] **MC-051-17** — Require architecture/security review for changes affecting semantics or trust boundaries.
- [ ] **MC-051-18** — Version document/evidence schemas and preserve immutable historical copies.
- [ ] **MC-051-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.
- [ ] **MC-051-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.
- [ ] **MC-051-21** — Make release approval depend on evidence completeness rather than document existence.

### D. Component-Specific Controls

- [ ] **MC-051-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.
- [ ] **MC-051-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.
- [ ] **MC-051-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.
- [ ] **MC-051-25** — Produce a normative design subsection specific to **Formal threat model** with valid and invalid worked examples.
- [ ] **MC-051-26** — Create an end-to-end integration fixture proving **Formal threat model** works through its real production-facing path.

### E. Implementation

- [ ] **MC-051-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-051-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-051-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-051-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-051-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-051-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-051-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-051-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-051-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-051-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-051-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-051-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-051-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-051-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-051-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-051-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-051-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-051-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-051-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-051-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-051-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-051-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-051-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-051-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-051-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-051-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-051-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-051-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-051-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-051-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-051-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-051-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-051-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-051-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-051-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-052 — Requirements traceability matrix

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Requirements traceability matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-052-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-052-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-052-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-052-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-052-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-052-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-052-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-052-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-052-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-052-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-052-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-052-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-052-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-052-14** — Assign a durable owner, reviewers, and review cadence.
- [ ] **MC-052-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.
- [ ] **MC-052-16** — Record assumptions and distinguish verified facts from design intent and deferred work.
- [ ] **MC-052-17** — Require architecture/security review for changes affecting semantics or trust boundaries.
- [ ] **MC-052-18** — Version document/evidence schemas and preserve immutable historical copies.
- [ ] **MC-052-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.
- [ ] **MC-052-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.
- [ ] **MC-052-21** — Make release approval depend on evidence completeness rather than document existence.

### D. Component-Specific Controls

- [ ] **MC-052-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-052-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-052-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-052-25** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.
- [ ] **MC-052-26** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.

### E. Implementation

- [ ] **MC-052-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-052-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-052-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-052-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-052-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-052-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-052-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-052-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-052-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-052-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-052-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-052-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-052-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-052-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-052-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-052-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-052-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-052-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-052-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-052-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-052-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-052-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-052-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-052-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-052-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-052-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-052-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-052-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-052-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-052-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-052-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-052-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-052-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-052-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-052-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-053 — Reproducible pk_core integration environment

**Category:** Build & CI  
**Implementation intent:** Deliver `Reproducible pk_core integration environment` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-053-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-053-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-053-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-053-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-053-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-053-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-053-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-053-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-053-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-053-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-053-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-053-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-053-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-053-14** — Pin toolchains, runners, base images, and third-party build actions/plugins by immutable version or digest.
- [ ] **MC-053-15** — Build from a clean workspace and prohibit undeclared network/download dependencies in certified jobs.
- [ ] **MC-053-16** — Use least-privilege short-lived credentials and isolate untrusted changes from signing/release credentials.
- [ ] **MC-053-17** — Make every mandatory stage fail closed on error, timeout, missing evidence, or skipped dependency.
- [ ] **MC-053-18** — Retain logs, reports, coverage, SBOMs, provenance, checksums, and test outputs as immutable artifacts.
- [ ] **MC-053-19** — Test the pipeline with deliberate failures so unenforced/bypassed gates are detected.
- [ ] **MC-053-20** — Provide deterministic local reproduction commands equivalent to CI stages.
- [ ] **MC-053-21** — Promote the exact tested artifact to release without rebuild drift.

### D. Component-Specific Controls

- [ ] **MC-053-22** — Bootstrap from a clean environment using pinned toolchains and dependency locks with no undeclared local state.
- [ ] **MC-053-23** — Fail the pipeline on missing/skipped mandatory gates and verify this with intentional negative pipeline tests.
- [ ] **MC-053-24** — Promote the exact tested artifact to release without rebuilding or mutating its content.
- [ ] **MC-053-25** — Produce a normative design subsection specific to **Reproducible pk_core integration environment** with valid and invalid worked examples.
- [ ] **MC-053-26** — Create an end-to-end integration fixture proving **Reproducible pk_core integration environment** works through its real production-facing path.

### E. Implementation

- [ ] **MC-053-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-053-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-053-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-053-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-053-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-053-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-053-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-053-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-053-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-053-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-053-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-053-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-053-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-053-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-053-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-053-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-053-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-053-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-053-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-053-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-053-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-053-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-053-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-053-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-053-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-053-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-053-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-053-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-053-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-053-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-053-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-053-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-053-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-053-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-053-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-054 — CI conformance pipeline

**Category:** Build & CI  
**Implementation intent:** Deliver `CI conformance pipeline` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-054-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-054-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-054-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-054-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-054-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-054-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-054-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-054-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-054-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-054-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-054-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-054-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-054-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-054-14** — Pin toolchains, runners, base images, and third-party build actions/plugins by immutable version or digest.
- [ ] **MC-054-15** — Build from a clean workspace and prohibit undeclared network/download dependencies in certified jobs.
- [ ] **MC-054-16** — Use least-privilege short-lived credentials and isolate untrusted changes from signing/release credentials.
- [ ] **MC-054-17** — Make every mandatory stage fail closed on error, timeout, missing evidence, or skipped dependency.
- [ ] **MC-054-18** — Retain logs, reports, coverage, SBOMs, provenance, checksums, and test outputs as immutable artifacts.
- [ ] **MC-054-19** — Test the pipeline with deliberate failures so unenforced/bypassed gates are detected.
- [ ] **MC-054-20** — Provide deterministic local reproduction commands equivalent to CI stages.
- [ ] **MC-054-21** — Promote the exact tested artifact to release without rebuild drift.

### D. Component-Specific Controls

- [ ] **MC-054-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-054-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-054-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-054-25** — Bootstrap from a clean environment using pinned toolchains and dependency locks with no undeclared local state.
- [ ] **MC-054-26** — Fail the pipeline on missing/skipped mandatory gates and verify this with intentional negative pipeline tests.

### E. Implementation

- [ ] **MC-054-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-054-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-054-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-054-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-054-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-054-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-054-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-054-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-054-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-054-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-054-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-054-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-054-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-054-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-054-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-054-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-054-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-054-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-054-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-054-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-054-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-054-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-054-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-054-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-054-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-054-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-054-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-054-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-054-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-054-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-054-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-054-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-054-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-054-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-054-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-055 — Release evidence bundle

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Release evidence bundle` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-055-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-055-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-055-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-055-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-055-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-055-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-055-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-055-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-055-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-055-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-055-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-055-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-055-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-055-14** — Assign a durable owner, reviewers, and review cadence.
- [ ] **MC-055-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.
- [ ] **MC-055-16** — Record assumptions and distinguish verified facts from design intent and deferred work.
- [ ] **MC-055-17** — Require architecture/security review for changes affecting semantics or trust boundaries.
- [ ] **MC-055-18** — Version document/evidence schemas and preserve immutable historical copies.
- [ ] **MC-055-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.
- [ ] **MC-055-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.
- [ ] **MC-055-21** — Make release approval depend on evidence completeness rather than document existence.

### D. Component-Specific Controls

- [ ] **MC-055-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.
- [ ] **MC-055-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.
- [ ] **MC-055-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.
- [ ] **MC-055-25** — Produce a normative design subsection specific to **Release evidence bundle** with valid and invalid worked examples.
- [ ] **MC-055-26** — Create an end-to-end integration fixture proving **Release evidence bundle** works through its real production-facing path.

### E. Implementation

- [ ] **MC-055-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-055-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-055-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-055-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-055-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-055-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-055-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-055-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-055-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-055-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-055-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-055-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-055-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-055-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-055-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-055-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-055-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-055-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-055-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-055-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-055-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-055-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-055-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-055-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-055-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-055-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-055-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-055-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-055-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-055-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-055-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-055-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-055-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-055-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-055-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-056 — Compatibility support matrix

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Compatibility support matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-056-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-056-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-056-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-056-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-056-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-056-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-056-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-056-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-056-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-056-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-056-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-056-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-056-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-056-14** — Assign a durable owner, reviewers, and review cadence.
- [ ] **MC-056-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.
- [ ] **MC-056-16** — Record assumptions and distinguish verified facts from design intent and deferred work.
- [ ] **MC-056-17** — Require architecture/security review for changes affecting semantics or trust boundaries.
- [ ] **MC-056-18** — Version document/evidence schemas and preserve immutable historical copies.
- [ ] **MC-056-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.
- [ ] **MC-056-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.
- [ ] **MC-056-21** — Make release approval depend on evidence completeness rather than document existence.

### D. Component-Specific Controls

- [ ] **MC-056-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.
- [ ] **MC-056-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.
- [ ] **MC-056-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.
- [ ] **MC-056-25** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.
- [ ] **MC-056-26** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.

### E. Implementation

- [ ] **MC-056-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-056-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-056-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-056-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-056-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-056-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-056-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-056-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-056-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-056-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-056-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-056-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-056-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-056-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-056-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-056-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-056-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-056-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-056-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-056-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-056-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-056-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-056-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-056-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-056-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-056-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-056-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-056-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-056-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-056-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-056-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-056-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-056-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-056-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-056-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-057 — Rollback and emergency-disable runbook

**Category:** Operations & Incident Response  
**Implementation intent:** Deliver `Rollback and emergency-disable runbook` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-057-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-057-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-057-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-057-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-057-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-057-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-057-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-057-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-057-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-057-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-057-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-057-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-057-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-057-14** — Define severity levels, activation criteria, and decision authority for incidents involving this component.
- [ ] **MC-057-15** — Provide exact tested containment/rollback commands with prerequisite and safety checks.
- [ ] **MC-057-16** — Preserve forensic evidence before destructive remediation when operational safety permits.
- [ ] **MC-057-17** — Define communication, escalation, ownership handoff, and status-update procedures.
- [ ] **MC-057-18** — Document consistency implications of rollback, restart, cancellation, forced teardown, and partial recovery.
- [ ] **MC-057-19** — Require post-action validation of semantic correctness, not merely process liveness.
- [ ] **MC-057-20** — Run recurring game days/tabletops and track remediation actions to closure.
- [ ] **MC-057-21** — Feed incident findings back into tests, alerts, limits, threat model, and release gates.

### D. Component-Specific Controls

- [ ] **MC-057-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.
- [ ] **MC-057-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.
- [ ] **MC-057-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.
- [ ] **MC-057-25** — Define exact trigger conditions, decision authority, commands, prerequisites, and abort criteria for emergency actions.
- [ ] **MC-057-26** — Preserve forensic evidence and state-consistency information before destructive remediation when safe to do so.

### E. Implementation

- [ ] **MC-057-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-057-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-057-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-057-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-057-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-057-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-057-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-057-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-057-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-057-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-057-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-057-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-057-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-057-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-057-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-057-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-057-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-057-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-057-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-057-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-057-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-057-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-057-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-057-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-057-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-057-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-057-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-057-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-057-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-057-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-057-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-057-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-057-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-057-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-057-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## MC-058 — Operational incident playbook

**Category:** Operations & Incident Response  
**Implementation intent:** Deliver `Operational incident playbook` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-058-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.
- [ ] **MC-058-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.
- [ ] **MC-058-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.
- [ ] **MC-058-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.
- [ ] **MC-058-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.
- [ ] **MC-058-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.

### B. Architecture & Data Model

- [ ] **MC-058-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.
- [ ] **MC-058-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.
- [ ] **MC-058-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.
- [ ] **MC-058-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.
- [ ] **MC-058-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.
- [ ] **MC-058-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.
- [ ] **MC-058-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.

### C. Domain-Specific Controls

- [ ] **MC-058-14** — Define severity levels, activation criteria, and decision authority for incidents involving this component.
- [ ] **MC-058-15** — Provide exact tested containment/rollback commands with prerequisite and safety checks.
- [ ] **MC-058-16** — Preserve forensic evidence before destructive remediation when operational safety permits.
- [ ] **MC-058-17** — Define communication, escalation, ownership handoff, and status-update procedures.
- [ ] **MC-058-18** — Document consistency implications of rollback, restart, cancellation, forced teardown, and partial recovery.
- [ ] **MC-058-19** — Require post-action validation of semantic correctness, not merely process liveness.
- [ ] **MC-058-20** — Run recurring game days/tabletops and track remediation actions to closure.
- [ ] **MC-058-21** — Feed incident findings back into tests, alerts, limits, threat model, and release gates.

### D. Component-Specific Controls

- [ ] **MC-058-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.
- [ ] **MC-058-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.
- [ ] **MC-058-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.
- [ ] **MC-058-25** — Define exact trigger conditions, decision authority, commands, prerequisites, and abort criteria for emergency actions.
- [ ] **MC-058-26** — Preserve forensic evidence and state-consistency information before destructive remediation when safe to do so.

### E. Implementation

- [ ] **MC-058-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.
- [ ] **MC-058-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.
- [ ] **MC-058-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.
- [ ] **MC-058-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.
- [ ] **MC-058-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.
- [ ] **MC-058-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.
- [ ] **MC-058-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.
- [ ] **MC-058-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.
- [ ] **MC-058-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.
- [ ] **MC-058-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.

### F. Security & Hardening

- [ ] **MC-058-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.
- [ ] **MC-058-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.
- [ ] **MC-058-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.
- [ ] **MC-058-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.
- [ ] **MC-058-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.
- [ ] **MC-058-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.

### G. Verification & Certification

- [ ] **MC-058-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.
- [ ] **MC-058-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.
- [ ] **MC-058-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.
- [ ] **MC-058-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.
- [ ] **MC-058-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.
- [ ] **MC-058-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.
- [ ] **MC-058-49** — Add a clean-environment release-mode certification test using only declared dependencies.
- [ ] **MC-058-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.

### H. Operations, Documentation & Release

- [ ] **MC-058-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.
- [ ] **MC-058-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.
- [ ] **MC-058-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.
- [ ] **MC-058-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.
- [ ] **MC-058-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.
- [ ] **MC-058-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.

### Definition of Done

- [ ] **MC-058-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.
- [ ] **MC-058-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.
- [ ] **MC-058-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.
- [ ] **MC-058-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.
- [ ] **MC-058-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.

---

## Program-level completion gates

- [ ] **PROGRAM-GATE-01** — All 58 component Definition-of-Done gates are satisfied or have formally approved time-bounded waivers.
- [ ] **PROGRAM-GATE-02** — The requirements traceability matrix contains no mandatory requirement without implementation and verification evidence.
- [ ] **PROGRAM-GATE-03** — The cross-language conformance matrix passes for every declared supported language/runtime pair.
- [ ] **PROGRAM-GATE-04** — The platform architecture matrix passes for every declared supported OS, CPU architecture, runtime, and feature profile.
- [ ] **PROGRAM-GATE-05** — Fuzzing, property-based, malicious-memory, concurrency, and leak/use-after-free suites have no unresolved release-blocking findings.
- [ ] **PROGRAM-GATE-06** — Performance/SLO certification is reproducible and includes large-payload, overload, fairness, and DoS behavior.
- [ ] **PROGRAM-GATE-07** — Threat-model mitigations are implemented, tested, and observable through audit/telemetry evidence.
- [ ] **PROGRAM-GATE-08** — Configuration, identity/capability, provenance, SBOM, trust-outage, and rollback controls have been exercised end to end.
- [ ] **PROGRAM-GATE-09** — The reproducible pk_core environment executes the external gate from a clean environment with retained results.
- [ ] **PROGRAM-GATE-10** — CI promotion releases the exact tested artifact; checksums, signatures/attestations, SBOM, provenance, and evidence are bundled.
- [ ] **PROGRAM-GATE-11** — Compatibility/support matrices are generated from passing evidence and match what the release actually supports.
- [ ] **PROGRAM-GATE-12** — Operational runbooks, rollback procedures, and incident playbooks have named owners and have been exercised in a game day/tabletop.
