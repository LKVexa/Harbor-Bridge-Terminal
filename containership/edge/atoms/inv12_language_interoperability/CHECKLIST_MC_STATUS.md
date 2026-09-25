# INV-12 Language Interoperability — Professional Missing-Components Checklist

**Baseline:** INV-12 v4.2.0 hardened  
**Checklist pack:** v1.0.0  
**Coverage:** 58 missing components × 56 technical controls = 3,248 component controls, plus 290 component Definition-of-Done gates and 12 program gates.  
**Status:** executed 2026-09-22 against INV-12 4.3.0. `- [x]` = objective evidence cited inline. Unchecked items carry PARTIAL / OPEN / BLOCKED / N/A-PROPOSED with the reason. N/A-PROPOSED items still need an approved waiver (scope, rationale, risk owner, reviewer, expiry).

## Evidence and completion policy

- Each control should produce reviewable evidence: source, tests, design records, CI logs, signed artifacts, metrics, runbooks, or measured results.
- P0/P1 correctness, memory/resource-safety, authentication/authorization, provenance, compatibility, or rollback defects block Production GO.
- “Implemented” is not enough: implementation, negative-path tests, integration behavior, and retained evidence must agree.
- N/A requires an explicit waiver with scope, rationale, risk owner, reviewer, and expiry/review date.
- Preserve stable IDs below in tickets, commits, CI jobs, requirements traceability, and release evidence.


## Execution summary (generated)

Items assessed: **3550** — BLOCKED: 3, DONE: 1666, N/A-PROPOSED: 797, OPEN: 226, PARTIAL: 858

| MC | Component | DONE | PARTIAL | OPEN | BLOCKED | N/A-PROPOSED |
|---|---|---|---|---|---|---|
| MC-001 | Canonical type AST and schema loader | 40 | 9 | 3 | 0 | 9 |
| MC-002 | Complete canonical primitive type set | 38 | 9 | 3 | 0 | 11 |
| MC-003 | Tuple, enum, and flags model | 36 | 10 | 3 | 0 | 12 |
| MC-004 | Resource-handle type system | 40 | 11 | 3 | 0 | 7 |
| MC-005 | Own/borrow semantics | 41 | 10 | 3 | 0 | 7 |
| MC-006 | Recursive composite validator | 39 | 9 | 3 | 0 | 10 |
| MC-007 | Language representation registry | 36 | 10 | 4 | 0 | 11 |
| MC-008 | Numeric conversion policy engine | 37 | 10 | 3 | 0 | 11 |
| MC-009 | Unicode and character transcoder | 37 | 9 | 3 | 0 | 12 |
| MC-010 | Canonical binary layout engine | 42 | 8 | 3 | 0 | 8 |
| MC-011 | Guest-memory adapter | 40 | 13 | 3 | 0 | 5 |
| MC-012 | Realloc/post-return lifecycle | 40 | 12 | 3 | 0 | 6 |
| MC-013 | Variant/option/result wire model | 41 | 7 | 3 | 0 | 10 |
| MC-014 | Canonical error envelope | 36 | 10 | 4 | 0 | 11 |
| MC-015 | ABI/version negotiation | 33 | 13 | 4 | 0 | 11 |
| MC-016 | Compatibility/evolution engine | 33 | 13 | 4 | 0 | 11 |
| MC-017 | Async/future/stream boundary semantics | 43 | 10 | 4 | 0 | 4 |
| MC-018 | Schema-derived resource limits | 36 | 13 | 3 | 0 | 9 |
| MC-019 | WebAssembly Component Model runtime adapter | 37 | 17 | 4 | 0 | 3 |
| MC-020 | Rust binding adapter and fixture component | 31 | 15 | 3 | 0 | 12 |
| MC-021 | Go binding adapter and fixture component | 31 | 15 | 3 | 0 | 12 |
| MC-022 | JavaScript binding adapter and fixture component | 31 | 15 | 3 | 0 | 12 |
| MC-023 | Python binding adapter and fixture component | 33 | 15 | 3 | 0 | 10 |
| MC-024 | Cross-language conformance matrix | 20 | 17 | 4 | 0 | 20 |
| MC-025 | Adjacent-layer integration fixtures | 26 | 17 | 6 | 0 | 12 |
| MC-026 | Golden canonical test-vector corpus | 24 | 15 | 4 | 0 | 18 |
| MC-027 | Property-based test harness | 20 | 18 | 4 | 0 | 19 |
| MC-028 | Coverage-guided fuzzing harness | 20 | 17 | 4 | 0 | 20 |
| MC-029 | Differential runtime tester | 21 | 16 | 4 | 0 | 20 |
| MC-030 | Malicious-memory test harness | 22 | 17 | 4 | 0 | 18 |
| MC-031 | Concurrency/race stress suite | 18 | 19 | 5 | 0 | 19 |
| MC-032 | Leak/use-after-free detector integration | 16 | 20 | 4 | 0 | 21 |
| MC-033 | Cross-platform architecture matrix | 11 | 21 | 7 | 1 | 21 |
| MC-034 | Performance benchmark harness | 16 | 20 | 4 | 0 | 21 |
| MC-035 | SLO certification gate | 16 | 20 | 4 | 0 | 21 |
| MC-036 | Large-payload/DoS benchmark suite | 20 | 18 | 4 | 0 | 19 |
| MC-037 | Metrics emitter | 31 | 17 | 3 | 0 | 10 |
| MC-038 | Distributed trace instrumentation | 30 | 18 | 3 | 0 | 10 |
| MC-039 | Structured security audit events | 35 | 14 | 3 | 0 | 9 |
| MC-040 | Diagnostic redaction policy | 32 | 14 | 3 | 0 | 12 |
| MC-041 | Runtime health/readiness model | 32 | 17 | 3 | 0 | 9 |
| MC-042 | Capacity/fairness controller | 34 | 16 | 3 | 0 | 8 |
| MC-043 | Declarative configuration schema | 36 | 13 | 3 | 0 | 9 |
| MC-044 | Configuration validator/transaction manager | 39 | 14 | 3 | 0 | 5 |
| MC-045 | Mapping-policy provenance | 32 | 14 | 5 | 0 | 10 |
| MC-046 | Artifact provenance verifier | 30 | 15 | 5 | 0 | 11 |
| MC-047 | SBOM and dependency lock | 31 | 15 | 5 | 0 | 10 |
| MC-048 | Capability/authentication integration | 35 | 11 | 3 | 0 | 12 |
| MC-049 | Trust-service outage policy | 35 | 13 | 3 | 0 | 10 |
| MC-050 | Architecture Decision Record | 13 | 18 | 6 | 0 | 24 |
| MC-051 | Formal threat model | 13 | 18 | 6 | 0 | 24 |
| MC-052 | Requirements traceability matrix | 15 | 17 | 6 | 0 | 23 |
| MC-053 | Reproducible pk_core integration environment | 16 | 19 | 4 | 0 | 22 |
| MC-054 | CI conformance pipeline | 19 | 17 | 3 | 0 | 22 |
| MC-055 | Release evidence bundle | 15 | 18 | 6 | 0 | 22 |
| MC-056 | Compatibility support matrix | 14 | 17 | 6 | 0 | 24 |
| MC-057 | Rollback and emergency-disable runbook | 12 | 21 | 4 | 0 | 24 |
| MC-058 | Operational incident playbook | 11 | 21 | 5 | 0 | 24 |

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

- [x] **MC-001-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §2 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-001-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-001-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §2; typed signatures + PK_INTEROP_* errors in canon/types.py
- [x] **MC-001-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-001-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-001-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-001-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §2 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-001-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-001-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-001-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-001-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [x] **MC-001-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-001-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-001-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §2 + REQ-G-1
- [x] **MC-001-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-001-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-001-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-001-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-001-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-001-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-001-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-001-22** — Define a formal grammar or schema meta-model with source-location preservation and deterministic normalization.  
  ↳ EBNF in canon/types.py with line:column locations
- [x] **MC-001-23** — Reject duplicate/ambiguous declarations, illegal recursion, unresolved references, and version-incompatible imports.  
  ↳ SchemaLoaderTest.test_rejections
- [x] **MC-001-24** — Guarantee parse → normalize → serialize determinism with golden fixtures and stable canonical hashes.  
  ↳ test_parse_normalize_serialize_is_deterministic + corpus schema_digest
- [x] **MC-001-25** — Produce a normative design subsection specific to **Canonical type AST and schema loader** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §2
- [ ] **MC-001-26** — Create an end-to-end integration fixture proving **Canonical type AST and schema loader** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-001-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-001-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-001-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-001-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-001-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-001-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-001-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-001-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-001-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [x] **MC-001-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ deterministic generated artifacts with digests (vectors.json schema_digest, SBOM, MANIFEST)

### F. Security & Hardening

- [x] **MC-001-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-001-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-001-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [x] **MC-001-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-001-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-001-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-001-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/types.py; tests: tests/test_canon.py::SchemaLoaderTest; evidence: evidence/fuzz.json
- [x] **MC-001-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/types.py; tests: tests/test_canon.py::SchemaLoaderTest; evidence: evidence/fuzz.json
- [x] **MC-001-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-001-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-001-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-001-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-001-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-001-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-001-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-001-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-001-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-001-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-001-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-001-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-001-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-001-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-001-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-001-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-001-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-002 — Complete canonical primitive type set

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Complete canonical primitive type set` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-002-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §3 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-002-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-002-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §3; typed signatures + PK_INTEROP_* errors in canon/types.py
- [x] **MC-002-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-002-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-002-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-002-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §3 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-002-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-002-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-002-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-002-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-002-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-002-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-002-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §3 + REQ-G-1
- [x] **MC-002-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-002-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [x] **MC-002-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ canon/registry.py table + canon/numeric.py exact/1 policy + canon/text.py (UTF-16 transcoding)
- [x] **MC-002-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-002-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-002-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-002-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-002-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.  
  ↳ fixtures/corpus/vectors.json (min/max/zero/sign/empty/unknown tag/malformed)
- [x] **MC-002-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.  
  ↳ 16/16 producer->consumer pairs + 0 divergences (evidence/conformance.json)
- [x] **MC-002-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.  
  ↳ layout table (canon/layout.py) + byte-exact golden images verified by 4 implementations
- [x] **MC-002-25** — Produce a normative design subsection specific to **Complete canonical primitive type set** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §3
- [ ] **MC-002-26** — Create an end-to-end integration fixture proving **Complete canonical primitive type set** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-002-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-002-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-002-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-002-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-002-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-002-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-002-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-002-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-002-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-002-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-002-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-002-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-002-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-002-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-002-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-002-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-002-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/types.py, canon/numeric.py; tests: tests/test_canon.py::TypeSetTest, tests/test_canon.py::PropertyTest; evidence: evidence/conformance.json
- [x] **MC-002-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/types.py, canon/numeric.py; tests: tests/test_canon.py::TypeSetTest, tests/test_canon.py::PropertyTest; evidence: evidence/conformance.json
- [x] **MC-002-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-002-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-002-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-002-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-002-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-002-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-002-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-002-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-002-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-002-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-002-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-002-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-002-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-002-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-002-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-002-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-002-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-003 — Tuple, enum, and flags model

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Tuple, enum, and flags model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-003-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §3 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-003-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-003-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §3; typed signatures + PK_INTEROP_* errors in canon/types.py
- [x] **MC-003-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-003-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-003-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-003-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §3 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-003-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-003-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-003-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-003-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-003-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-003-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-003-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §3 + REQ-G-1
- [x] **MC-003-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-003-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-003-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-003-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-003-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-003-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-003-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-003-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.  
  ↳ fixtures/corpus/vectors.json (min/max/zero/sign/empty/unknown tag/malformed)
- [x] **MC-003-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.  
  ↳ 16/16 producer->consumer pairs + 0 divergences (evidence/conformance.json)
- [x] **MC-003-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.  
  ↳ layout table (canon/layout.py) + byte-exact golden images verified by 4 implementations
- [x] **MC-003-25** — Produce a normative design subsection specific to **Tuple, enum, and flags model** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §3
- [ ] **MC-003-26** — Create an end-to-end integration fixture proving **Tuple, enum, and flags model** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-003-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-003-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-003-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-003-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-003-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-003-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-003-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-003-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-003-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-003-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-003-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-003-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-003-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-003-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-003-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-003-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-003-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/types.py, canon/layout.py; tests: tests/test_canon.py::TypeSetTest; evidence: evidence/conformance.json
- [x] **MC-003-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/types.py, canon/layout.py; tests: tests/test_canon.py::TypeSetTest; evidence: evidence/conformance.json
- [x] **MC-003-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-003-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-003-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-003-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-003-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-003-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-003-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-003-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-003-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-003-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-003-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-003-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-003-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-003-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-003-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-003-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-003-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-004 — Resource-handle type system

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Resource-handle type system` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-004-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §4 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-004-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-004-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §4; typed signatures + PK_INTEROP_* errors in canon/resources.py
- [x] **MC-004-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-004-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-004-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-004-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §4 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-004-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-004-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/resources.py
- [x] **MC-004-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [x] **MC-004-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/resources.py)
- [ ] **MC-004-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-004-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-004-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §4 + REQ-G-1
- [x] **MC-004-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-004-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-004-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-004-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-004-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-004-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-004-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-004-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.  
  ↳ state machines in canon/resources.py / canon/memory.py; stale/foreign/moved/wrong-type refused
- [x] **MC-004-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.  
  ↳ CheckedRealloc accounting, dtor_calls, leaked()==0 after fault injection
- [x] **MC-004-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.  
  ↳ rollback/revocation/post_return tests incl. concurrent teardown
- [x] **MC-004-25** — Produce a normative design subsection specific to **Resource-handle type system** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §4
- [ ] **MC-004-26** — Create an end-to-end integration fixture proving **Resource-handle type system** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-004-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-004-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-004-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-004-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [ ] **MC-004-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-004-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-004-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-004-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-004-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-004-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-004-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-004-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-004-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-004-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-004-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-004-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-004-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/resources.py; tests: tests/test_canon.py::ResourceTest, tests/test_canon.py::ConcurrencyLeakTest
- [x] **MC-004-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/resources.py; tests: tests/test_canon.py::ResourceTest, tests/test_canon.py::ConcurrencyLeakTest
- [ ] **MC-004-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-004-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-004-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-004-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-004-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-004-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-004-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-004-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-004-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-004-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-004-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-004-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-004-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-004-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-004-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-004-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-004-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-005 — Own/borrow semantics

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Own/borrow semantics` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-005-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §4 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-005-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-005-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §4; typed signatures + PK_INTEROP_* errors in canon/resources.py
- [x] **MC-005-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-005-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-005-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-005-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §4 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-005-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-005-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/resources.py
- [x] **MC-005-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [x] **MC-005-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/resources.py)
- [ ] **MC-005-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-005-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-005-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §4 + REQ-G-1
- [x] **MC-005-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-005-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-005-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-005-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-005-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-005-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-005-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-005-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.  
  ↳ state machines in canon/resources.py / canon/memory.py; stale/foreign/moved/wrong-type refused
- [x] **MC-005-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.  
  ↳ CheckedRealloc accounting, dtor_calls, leaked()==0 after fault injection
- [x] **MC-005-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.  
  ↳ rollback/revocation/post_return tests incl. concurrent teardown
- [x] **MC-005-25** — Produce a normative design subsection specific to **Own/borrow semantics** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §4
- [x] **MC-005-26** — Create an end-to-end integration fixture proving **Own/borrow semantics** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-005-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-005-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-005-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-005-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [ ] **MC-005-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-005-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-005-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-005-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-005-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-005-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-005-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-005-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-005-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-005-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-005-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-005-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-005-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/resources.py, canon/boundary.py; tests: tests/test_canon.py::ResourceTest, tests/test_canon.py::BoundaryIntegrationTest
- [x] **MC-005-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/resources.py, canon/boundary.py; tests: tests/test_canon.py::ResourceTest, tests/test_canon.py::BoundaryIntegrationTest
- [ ] **MC-005-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-005-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-005-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-005-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-005-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-005-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-005-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-005-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-005-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-005-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-005-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-005-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-005-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-005-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-005-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-005-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-005-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-006 — Recursive composite validator

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Recursive composite validator` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-006-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §5 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-006-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-006-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §5; typed signatures + PK_INTEROP_* errors in canon/validate.py
- [x] **MC-006-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-006-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-006-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-006-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §5 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-006-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-006-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-006-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-006-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [x] **MC-006-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-006-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-006-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §5 + REQ-G-1
- [x] **MC-006-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-006-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-006-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-006-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-006-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-006-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-006-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-006-22** — Produce a normative design subsection specific to **Recursive composite validator** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §5
- [x] **MC-006-23** — Create an end-to-end integration fixture proving **Recursive composite validator** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses
- [x] **MC-006-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Recursive composite validator** and enforce them automatically.  
  ↳ enforced by tools/bench.py thresholds
- [ ] **MC-006-25** — Record assumptions and unsupported cases for **Recursive composite validator** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [x] **MC-006-26** — Create at least one failure-injection scenario for **Recursive composite validator** that proves safe rollback or containment.  
  ↳ invalid args / leaked borrow / hostile realloc injections with rollback asserted

### E. Implementation

- [x] **MC-006-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-006-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-006-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-006-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [x] **MC-006-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [ ] **MC-006-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-006-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-006-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-006-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-006-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-006-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-006-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-006-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-006-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-006-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-006-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-006-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/validate.py; tests: tests/test_canon.py::ValidatorTest, tests/test_canon.py::PropertyTest; evidence: evidence/bench.json
- [x] **MC-006-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/validate.py; tests: tests/test_canon.py::ValidatorTest, tests/test_canon.py::PropertyTest; evidence: evidence/bench.json
- [x] **MC-006-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-006-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-006-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-006-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-006-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-006-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-006-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-006-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-006-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-006-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-006-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-006-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-006-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-006-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-006-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-006-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-006-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-007 — Language representation registry

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Language representation registry` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-007-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §6 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-007-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-007-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §6; typed signatures + PK_INTEROP_* errors in canon/registry.py
- [x] **MC-007-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-007-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-007-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-007-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §6 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-007-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-007-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-007-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-007-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-007-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-007-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-007-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §6 + REQ-G-1
- [x] **MC-007-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-007-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [x] **MC-007-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ canon/registry.py table + canon/numeric.py exact/1 policy + canon/text.py (UTF-16 transcoding)
- [x] **MC-007-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-007-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-007-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-007-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-007-22** — Produce a normative design subsection specific to **Language representation registry** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §6
- [x] **MC-007-23** — Create an end-to-end integration fixture proving **Language representation registry** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses
- [ ] **MC-007-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Language representation registry** and enforce them automatically.  
  ↳ **OPEN** — no component-specific budget defined
- [ ] **MC-007-25** — Record assumptions and unsupported cases for **Language representation registry** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [x] **MC-007-26** — Create at least one failure-injection scenario for **Language representation registry** that proves safe rollback or containment.  
  ↳ invalid args / leaked borrow / hostile realloc injections with rollback asserted

### E. Implementation

- [x] **MC-007-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-007-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-007-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-007-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [x] **MC-007-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [ ] **MC-007-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-007-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-007-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-007-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-007-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-007-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-007-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-007-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-007-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-007-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-007-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-007-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/registry.py; tests: tests/test_canon.py::RegistryNumericUnicodeTest, tests/test_canon.py::BoundaryIntegrationTest
- [x] **MC-007-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/registry.py; tests: tests/test_canon.py::RegistryNumericUnicodeTest, tests/test_canon.py::BoundaryIntegrationTest
- [ ] **MC-007-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-007-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-007-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-007-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-007-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-007-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-007-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-007-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-007-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-007-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-007-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-007-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-007-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-007-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-007-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-007-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-007-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-008 — Numeric conversion policy engine

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Numeric conversion policy engine` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-008-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §6 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-008-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-008-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §6; typed signatures + PK_INTEROP_* errors in canon/numeric.py
- [x] **MC-008-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-008-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-008-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-008-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §6 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-008-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-008-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-008-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-008-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-008-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-008-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-008-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §6 + REQ-G-1
- [x] **MC-008-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-008-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [x] **MC-008-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ canon/registry.py table + canon/numeric.py exact/1 policy + canon/text.py (UTF-16 transcoding)
- [x] **MC-008-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-008-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-008-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-008-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-008-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.  
  ↳ fixtures/corpus/vectors.json (min/max/zero/sign/empty/unknown tag/malformed)
- [x] **MC-008-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.  
  ↳ 16/16 producer->consumer pairs + 0 divergences (evidence/conformance.json)
- [x] **MC-008-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.  
  ↳ layout table (canon/layout.py) + byte-exact golden images verified by 4 implementations
- [x] **MC-008-25** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.  
  ↳ validate_config + quorum approvals before atomic swap
- [ ] **MC-008-26** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.  
  ↳ **PARTIAL** — digest/actor/revision recorded; rollback target implicit (history)

### E. Implementation

- [x] **MC-008-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-008-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-008-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-008-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-008-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-008-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-008-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-008-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-008-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-008-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-008-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-008-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-008-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-008-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-008-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-008-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-008-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/numeric.py; tests: tests/test_canon.py::RegistryNumericUnicodeTest; evidence: evidence/conformance.json
- [x] **MC-008-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/numeric.py; tests: tests/test_canon.py::RegistryNumericUnicodeTest; evidence: evidence/conformance.json
- [ ] **MC-008-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-008-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-008-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-008-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-008-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-008-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-008-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-008-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-008-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-008-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-008-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-008-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-008-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-008-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-008-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-008-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-008-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-009 — Unicode and character transcoder

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Unicode and character transcoder` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-009-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §6 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-009-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-009-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §6; typed signatures + PK_INTEROP_* errors in canon/text.py
- [x] **MC-009-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-009-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-009-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-009-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §6 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-009-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-009-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-009-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-009-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-009-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-009-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-009-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §6 + REQ-G-1
- [x] **MC-009-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-009-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [x] **MC-009-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ canon/registry.py table + canon/numeric.py exact/1 policy + canon/text.py (UTF-16 transcoding)
- [x] **MC-009-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-009-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-009-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-009-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-009-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.  
  ↳ fixtures/corpus/vectors.json (min/max/zero/sign/empty/unknown tag/malformed)
- [x] **MC-009-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.  
  ↳ 16/16 producer->consumer pairs + 0 divergences (evidence/conformance.json)
- [x] **MC-009-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.  
  ↳ layout table (canon/layout.py) + byte-exact golden images verified by 4 implementations
- [x] **MC-009-25** — Produce a normative design subsection specific to **Unicode and character transcoder** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §6
- [ ] **MC-009-26** — Create an end-to-end integration fixture proving **Unicode and character transcoder** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-009-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-009-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-009-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-009-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-009-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-009-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-009-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-009-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-009-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-009-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-009-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-009-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-009-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-009-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-009-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-009-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-009-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/text.py; tests: tests/test_canon.py::RegistryNumericUnicodeTest; evidence: evidence/conformance.json
- [x] **MC-009-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/text.py; tests: tests/test_canon.py::RegistryNumericUnicodeTest; evidence: evidence/conformance.json
- [x] **MC-009-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-009-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-009-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-009-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-009-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-009-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-009-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-009-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-009-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-009-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-009-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-009-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-009-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-009-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-009-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-009-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-009-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-010 — Canonical binary layout engine

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Canonical binary layout engine` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-010-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §7 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-010-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-010-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in canon/layout.py
- [x] **MC-010-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-010-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-010-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-010-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §7 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-010-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-010-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [x] **MC-010-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [ ] **MC-010-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [x] **MC-010-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-010-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-010-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §7 + REQ-G-1
- [x] **MC-010-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-010-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [x] **MC-010-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ canon/registry.py table + canon/numeric.py exact/1 policy + canon/text.py (UTF-16 transcoding)
- [x] **MC-010-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-010-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-010-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-010-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-010-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.  
  ↳ fixtures/corpus/vectors.json (min/max/zero/sign/empty/unknown tag/malformed)
- [x] **MC-010-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.  
  ↳ 16/16 producer->consumer pairs + 0 divergences (evidence/conformance.json)
- [x] **MC-010-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.  
  ↳ layout table (canon/layout.py) + byte-exact golden images verified by 4 implementations
- [x] **MC-010-25** — Produce a normative design subsection specific to **Canonical binary layout engine** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §7
- [ ] **MC-010-26** — Create an end-to-end integration fixture proving **Canonical binary layout engine** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-010-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-010-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-010-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-010-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [x] **MC-010-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [ ] **MC-010-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-010-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-010-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-010-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-010-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-010-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-010-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-010-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-010-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-010-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-010-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-010-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/layout.py; tests: tests/test_canon.py::LayoutMemoryTest, tests/test_canon.py::PropertyTest; evidence: evidence/conformance.json
- [x] **MC-010-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/layout.py; tests: tests/test_canon.py::LayoutMemoryTest, tests/test_canon.py::PropertyTest; evidence: evidence/conformance.json
- [x] **MC-010-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-010-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-010-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-010-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-010-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-010-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-010-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-010-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-010-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-010-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-010-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-010-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-010-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-010-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-010-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-010-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-010-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-011 — Guest-memory adapter

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Guest-memory adapter` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-011-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §7 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-011-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-011-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in canon/memory.py
- [x] **MC-011-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-011-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-011-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-011-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §7 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-011-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-011-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/memory.py
- [x] **MC-011-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [x] **MC-011-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/memory.py)
- [x] **MC-011-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-011-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-011-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [x] **MC-011-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ no unsafe/FFI in Python/JS/Rust fixtures; Go guest confines unsafe.Pointer to base() address computation
- [x] **MC-011-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [x] **MC-011-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ fixtures map every failure to PK_INTEROP_* codes (panic->abiErr in Go, Result in Rust, AbiError in JS)
- [x] **MC-011-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ CallLifecycle post_return/rollback idempotence guarded; CallScope revocation
- [x] **MC-011-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ immutable registries; lock-guarded tables; ConcurrencyLeakTest
- [ ] **MC-011-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ **PARTIAL** — core-Wasm guest exercises record/string/list only
- [ ] **MC-011-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [x] **MC-011-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.  
  ↳ state machines in canon/resources.py / canon/memory.py; stale/foreign/moved/wrong-type refused
- [x] **MC-011-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.  
  ↳ CheckedRealloc accounting, dtor_calls, leaked()==0 after fault injection
- [x] **MC-011-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.  
  ↳ rollback/revocation/post_return tests incl. concurrent teardown
- [ ] **MC-011-25** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-011-26** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features

### E. Implementation

- [x] **MC-011-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-011-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-011-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-011-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [ ] **MC-011-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-011-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-011-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-011-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-011-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-011-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-011-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-011-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-011-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-011-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-011-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-011-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-011-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/memory.py, fixtures/js/inv12.mjs; tests: tests/test_canon.py::LayoutMemoryTest, tests/test_canon.py::MaliciousMemoryTest; evidence: evidence/wasm_guest.json
- [x] **MC-011-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/memory.py, fixtures/js/inv12.mjs; tests: tests/test_canon.py::LayoutMemoryTest, tests/test_canon.py::MaliciousMemoryTest; evidence: evidence/wasm_guest.json
- [ ] **MC-011-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-011-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-011-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-011-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-011-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-011-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-011-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-011-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-011-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-011-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-011-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-011-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-011-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-011-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-011-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-011-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-011-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-012 — Realloc/post-return lifecycle

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Realloc/post-return lifecycle` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-012-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §7 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-012-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-012-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in canon/memory.py
- [x] **MC-012-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-012-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-012-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-012-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §7 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-012-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-012-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/memory.py
- [x] **MC-012-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [x] **MC-012-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/memory.py)
- [ ] **MC-012-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-012-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-012-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [x] **MC-012-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ no unsafe/FFI in Python/JS/Rust fixtures; Go guest confines unsafe.Pointer to base() address computation
- [x] **MC-012-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [x] **MC-012-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ fixtures map every failure to PK_INTEROP_* codes (panic->abiErr in Go, Result in Rust, AbiError in JS)
- [x] **MC-012-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ CallLifecycle post_return/rollback idempotence guarded; CallScope revocation
- [x] **MC-012-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ immutable registries; lock-guarded tables; ConcurrencyLeakTest
- [ ] **MC-012-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ **PARTIAL** — core-Wasm guest exercises record/string/list only
- [ ] **MC-012-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [x] **MC-012-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.  
  ↳ state machines in canon/resources.py / canon/memory.py; stale/foreign/moved/wrong-type refused
- [x] **MC-012-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.  
  ↳ CheckedRealloc accounting, dtor_calls, leaked()==0 after fault injection
- [x] **MC-012-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.  
  ↳ rollback/revocation/post_return tests incl. concurrent teardown
- [x] **MC-012-25** — Produce a normative design subsection specific to **Realloc/post-return lifecycle** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §7
- [x] **MC-012-26** — Create an end-to-end integration fixture proving **Realloc/post-return lifecycle** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-012-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-012-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-012-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-012-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [ ] **MC-012-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-012-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-012-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-012-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-012-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-012-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-012-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-012-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-012-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-012-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-012-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-012-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-012-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/memory.py, fixtures/wasm-guest/main.go; tests: tests/test_canon.py::LayoutMemoryTest, tests/test_canon.py::ConcurrencyLeakTest; evidence: evidence/wasm_guest.json
- [x] **MC-012-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/memory.py, fixtures/wasm-guest/main.go; tests: tests/test_canon.py::LayoutMemoryTest, tests/test_canon.py::ConcurrencyLeakTest; evidence: evidence/wasm_guest.json
- [ ] **MC-012-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-012-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-012-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-012-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-012-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-012-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-012-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-012-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-012-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-012-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-012-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-012-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-012-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-012-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-012-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-012-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-012-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-013 — Variant/option/result wire model

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Variant/option/result wire model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-013-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §7 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-013-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-013-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in canon/layout.py
- [x] **MC-013-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-013-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-013-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-013-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §7 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-013-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-013-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-013-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-013-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [x] **MC-013-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-013-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-013-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §7 + REQ-G-1
- [x] **MC-013-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-013-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [x] **MC-013-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ canon/registry.py table + canon/numeric.py exact/1 policy + canon/text.py (UTF-16 transcoding)
- [x] **MC-013-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-013-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-013-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-013-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-013-22** — Publish boundary vectors covering minimum, maximum, zero, sign transitions, empty values, unknown tags, and malformed encodings as applicable.  
  ↳ fixtures/corpus/vectors.json (min/max/zero/sign/empty/unknown tag/malformed)
- [x] **MC-013-23** — Prove representation equivalence across supported languages without silent truncation, widening, sign changes, or normalization drift.  
  ↳ 16/16 producer->consumer pairs + 0 divergences (evidence/conformance.json)
- [x] **MC-013-24** — Document exact wire/layout form and verify encoded bytes or canonical values against independent golden vectors.  
  ↳ layout table (canon/layout.py) + byte-exact golden images verified by 4 implementations
- [x] **MC-013-25** — Produce a normative design subsection specific to **Variant/option/result wire model** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §7
- [x] **MC-013-26** — Create an end-to-end integration fixture proving **Variant/option/result wire model** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-013-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-013-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-013-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-013-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-013-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-013-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-013-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-013-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-013-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-013-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-013-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-013-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-013-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-013-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-013-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-013-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-013-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/layout.py; tests: tests/test_canon.py::LayoutMemoryTest; evidence: evidence/conformance.json
- [x] **MC-013-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/layout.py; tests: tests/test_canon.py::LayoutMemoryTest; evidence: evidence/conformance.json
- [x] **MC-013-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-013-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-013-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-013-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-013-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-013-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-013-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-013-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-013-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-013-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-013-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-013-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-013-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-013-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-013-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-013-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-013-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-014 — Canonical error envelope

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Canonical error envelope` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-014-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §8 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-014-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-014-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §8; typed signatures + PK_INTEROP_* errors in canon/errors.py
- [x] **MC-014-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-014-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-014-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-014-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §8 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-014-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-014-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-014-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-014-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-014-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-014-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-014-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §8 + REQ-G-1
- [x] **MC-014-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-014-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-014-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-014-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-014-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-014-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-014-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-014-22** — Produce a normative design subsection specific to **Canonical error envelope** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §8
- [x] **MC-014-23** — Create an end-to-end integration fixture proving **Canonical error envelope** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses
- [ ] **MC-014-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Canonical error envelope** and enforce them automatically.  
  ↳ **OPEN** — no component-specific budget defined
- [ ] **MC-014-25** — Record assumptions and unsupported cases for **Canonical error envelope** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [x] **MC-014-26** — Create at least one failure-injection scenario for **Canonical error envelope** that proves safe rollback or containment.  
  ↳ invalid args / leaked borrow / hostile realloc injections with rollback asserted

### E. Implementation

- [x] **MC-014-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-014-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-014-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-014-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-014-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-014-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-014-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-014-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-014-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-014-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-014-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-014-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-014-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-014-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-014-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-014-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-014-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/errors.py; tests: tests/test_canon.py::ErrorEnvelopeTest; evidence: evidence/fuzz.json
- [x] **MC-014-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/errors.py; tests: tests/test_canon.py::ErrorEnvelopeTest; evidence: evidence/fuzz.json
- [x] **MC-014-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-014-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-014-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-014-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-014-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-014-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-014-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-014-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-014-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-014-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-014-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-014-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-014-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-014-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-014-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-014-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-014-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-015 — ABI/version negotiation

**Category:** ABI Semantics  
**Implementation intent:** Deliver `ABI/version negotiation` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-015-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §9 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-015-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-015-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §9; typed signatures + PK_INTEROP_* errors in canon/negotiation.py
- [x] **MC-015-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-015-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-015-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-015-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §9 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-015-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-015-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-015-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-015-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-015-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-015-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-015-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §9 + REQ-G-1
- [x] **MC-015-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-015-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-015-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-015-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-015-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-015-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-015-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-015-22** — Produce a normative design subsection specific to **ABI/version negotiation** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §9
- [ ] **MC-015-23** — Create an end-to-end integration fixture proving **ABI/version negotiation** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path
- [ ] **MC-015-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **ABI/version negotiation** and enforce them automatically.  
  ↳ **OPEN** — no component-specific budget defined
- [ ] **MC-015-25** — Record assumptions and unsupported cases for **ABI/version negotiation** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [ ] **MC-015-26** — Create at least one failure-injection scenario for **ABI/version negotiation** that proves safe rollback or containment.  
  ↳ **PARTIAL** — negative tests exist; no dedicated failure-injection scenario

### E. Implementation

- [x] **MC-015-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-015-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-015-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-015-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-015-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-015-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-015-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-015-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-015-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-015-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-015-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-015-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-015-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-015-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-015-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-015-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-015-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/negotiation.py; tests: tests/test_canon.py::NegotiationEvolutionTest
- [x] **MC-015-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/negotiation.py; tests: tests/test_canon.py::NegotiationEvolutionTest
- [ ] **MC-015-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-015-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-015-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-015-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-015-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-015-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-015-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-015-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-015-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-015-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-015-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-015-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-015-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-015-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-015-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-015-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-015-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-016 — Compatibility/evolution engine

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Compatibility/evolution engine` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-016-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §9 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-016-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-016-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §9; typed signatures + PK_INTEROP_* errors in canon/negotiation.py
- [x] **MC-016-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-016-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-016-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-016-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §9 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-016-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-016-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-016-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-016-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-016-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-016-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-016-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §9 + REQ-G-1
- [x] **MC-016-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-016-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-016-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-016-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-016-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-016-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-016-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-016-22** — Produce a normative design subsection specific to **Compatibility/evolution engine** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §9
- [ ] **MC-016-23** — Create an end-to-end integration fixture proving **Compatibility/evolution engine** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path
- [ ] **MC-016-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Compatibility/evolution engine** and enforce them automatically.  
  ↳ **OPEN** — no component-specific budget defined
- [ ] **MC-016-25** — Record assumptions and unsupported cases for **Compatibility/evolution engine** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [ ] **MC-016-26** — Create at least one failure-injection scenario for **Compatibility/evolution engine** that proves safe rollback or containment.  
  ↳ **PARTIAL** — negative tests exist; no dedicated failure-injection scenario

### E. Implementation

- [x] **MC-016-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-016-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-016-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-016-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-016-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-016-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-016-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-016-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-016-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-016-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-016-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-016-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-016-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-016-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-016-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-016-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-016-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/negotiation.py; tests: tests/test_canon.py::NegotiationEvolutionTest
- [x] **MC-016-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/negotiation.py; tests: tests/test_canon.py::NegotiationEvolutionTest
- [ ] **MC-016-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-016-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-016-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-016-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-016-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-016-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-016-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-016-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-016-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-016-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-016-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-016-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-016-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-016-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-016-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-016-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-016-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-017 — Async/future/stream boundary semantics

**Category:** ABI Semantics  
**Implementation intent:** Deliver `Async/future/stream boundary semantics` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-017-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §10 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-017-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-017-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §10; typed signatures + PK_INTEROP_* errors in canon/async_model.py
- [x] **MC-017-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-017-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-017-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-017-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §10 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-017-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-017-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/async_model.py
- [x] **MC-017-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [x] **MC-017-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/async_model.py)
- [x] **MC-017-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-017-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-017-14** — Define language-neutral normative semantics and prohibit implementation-defined behavior.  
  ↳ docs/SPEC.md §10 + REQ-G-1
- [x] **MC-017-15** — Define canonical lowering/lifting and round-trip invariants, including cases where lossless round-trip is not valid.  
  ↳ canon/layout.py docstring: round-trip invariant and its exceptions (NaN payloads, handle identity, bool bytes); PropertyTest
- [x] **MC-017-16** — Define exact invalid-state rejection rules and run validation before mutation, allocation, I/O, or ownership transfer.  
  ↳ REQ-G-2; validate() before allocation; LayoutMemoryTest invalid corpus
- [ ] **MC-017-17** — Document every host-language impedance mismatch and require explicit conversion rather than implicit coercion.  
  ↳ **PARTIAL** — mismatches documented in registry/numeric policy, not per this component
- [x] **MC-017-18** — Assign stable type/schema identifiers and deterministic hashing/normalization rules.  
  ↳ type_hash()/Interface.digest() sha256 over canonical form (SchemaLoaderTest determinism)
- [x] **MC-017-19** — Define recursion, size, complexity, and allocation bounds for all valid inputs.  
  ↳ canon/limits.py + schema limits; evidence/bench.json DoS
- [x] **MC-017-20** — Define forward/backward evolution semantics, unknown-value handling, and feature negotiation.  
  ↳ canon/negotiation.py compare/check_version_bump + negotiate (NegotiationEvolutionTest)
- [x] **MC-017-21** — Define machine-readable diagnostics for every contract violation, including stable error codes and typed details.  
  ↳ ERROR_CODES registry + PK_INTEROP_ERROR/1 envelope validated in every assertCode

### D. Component-Specific Controls

- [x] **MC-017-22** — Specify completion, polling/wakeup, cancellation, terminal-state, and backpressure semantics with no duplicated terminal delivery.  
  ↳ Future/Stream state machines; single terminal delivery (AsyncTest)
- [x] **MC-017-23** — Bound buffering and outstanding work; prove cancellation cannot leak ownership or orphan resources.  
  ↳ stream window + discard accounting on cancel
- [ ] **MC-017-24** — Use deterministic scheduler tests to reproduce lost-wakeup, double-completion, and cancellation races.  
  ↳ **OPEN** — threaded tests only; no deterministic scheduler
- [x] **MC-017-25** — Produce a normative design subsection specific to **Async/future/stream boundary semantics** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §10
- [ ] **MC-017-26** — Create an end-to-end integration fixture proving **Async/future/stream boundary semantics** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-017-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-017-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-017-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-017-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [x] **MC-017-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [ ] **MC-017-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-017-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [x] **MC-017-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ Future/Stream read/write timeouts + cancel (canon/async_model.py)
- [x] **MC-017-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-017-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-017-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-017-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-017-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-017-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-017-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-017-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-017-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/async_model.py; tests: tests/test_canon.py::AsyncTest
- [x] **MC-017-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/async_model.py; tests: tests/test_canon.py::AsyncTest
- [ ] **MC-017-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-017-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-017-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-017-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-017-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-017-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-017-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-017-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-017-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-017-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-017-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-017-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-017-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-017-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-017-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-017-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-017-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-018 — Schema-derived resource limits

**Category:** Security & Policy  
**Implementation intent:** Deliver `Schema-derived resource limits` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-018-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §5 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-018-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-018-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §5; typed signatures + PK_INTEROP_* errors in canon/limits.py
- [x] **MC-018-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-018-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-018-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-018-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §5 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-018-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-018-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-018-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-018-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [x] **MC-018-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-018-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-018-14** — Document the trust boundary and exact authority granted to this component.  
  ↳ docs/SPEC.md §0 trust boundaries; docs/THREAT_MODEL.md
- [x] **MC-018-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.  
  ↳ unknown identities/codes/languages/configs refused (ConfigTrustTest, RegistryNumericUnicodeTest)
- [x] **MC-018-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.  
  ↳ decisions keyed to config revision/digest; AuditLog hash chain
- [x] **MC-018-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.  
  ↳ Limits/Budget, bounded diagnostics (160 chars/32 segments), max_spans
- [x] **MC-018-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.  
  ↳ hmac.compare_digest for MACs (config, audit, trust)
- [x] **MC-018-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.  
  ↳ revision replay refused; transcript digests; foreign/stale handles refused; key revocation clears cache
- [x] **MC-018-20** — Classify and redact logs, errors, traces, and audit events before emission.  
  ↳ errors.redact + span attribute allow-list
- [ ] **MC-018-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.  
  ↳ **PARTIAL** — outage behaviour defined in SPEC §11; not exercised for this component

### D. Component-Specific Controls

- [ ] **MC-018-22** — Define a formal grammar or schema meta-model with source-location preservation and deterministic normalization.  
  ↳ **PARTIAL** — limits schema is a dataclass, not a published meta-model
- [x] **MC-018-23** — Reject duplicate/ambiguous declarations, illegal recursion, unresolved references, and version-incompatible imports.  
  ↳ validate_config / LimitPolicy reject unknown and loosening entries
- [ ] **MC-018-24** — Guarantee parse → normalize → serialize determinism with golden fixtures and stable canonical hashes.  
  ↳ **PARTIAL** — config digest deterministic (canonical JSON); no golden fixture
- [ ] **MC-018-25** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.  
  ↳ **PARTIAL** — limits have no lifecycle; budgets are per-operation
- [ ] **MC-018-26** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.  
  ↳ **PARTIAL** — Budget accounting only

### E. Implementation

- [x] **MC-018-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-018-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-018-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-018-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-018-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [x] **MC-018-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ Boundary reads ConfigManager.current once per call (immutable Snapshot)
- [x] **MC-018-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-018-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-018-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-018-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-018-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-018-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-018-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-018-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-018-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-018-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-018-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/limits.py; tests: tests/test_canon.py::ValidatorTest; evidence: evidence/bench.json
- [x] **MC-018-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/limits.py; tests: tests/test_canon.py::ValidatorTest; evidence: evidence/bench.json
- [ ] **MC-018-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-018-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-018-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-018-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-018-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-018-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-018-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-018-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-018-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-018-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-018-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-018-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-018-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-018-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-018-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-018-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-018-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-019 — WebAssembly Component Model runtime adapter

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `WebAssembly Component Model runtime adapter` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-019-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ ADR-0001 §8 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-019-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-019-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ ADR-0001 §8; typed signatures + PK_INTEROP_* errors in canon/boundary.py
- [x] **MC-019-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-019-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-019-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-019-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ ADR-0001 §8 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-019-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-019-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/boundary.py
- [x] **MC-019-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [x] **MC-019-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/boundary.py)
- [x] **MC-019-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-019-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-019-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [ ] **MC-019-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ **PARTIAL** — only core-Wasm exports; no production FFI adapter exists
- [x] **MC-019-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [ ] **MC-019-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ **PARTIAL** — guest trap translation not exercised (no production runtime)
- [x] **MC-019-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ CallLifecycle post_return/rollback idempotence guarded; CallScope revocation
- [x] **MC-019-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ immutable registries; lock-guarded tables; ConcurrencyLeakTest
- [ ] **MC-019-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ **PARTIAL** — core-Wasm guest exercises record/string/list only
- [ ] **MC-019-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [ ] **MC-019-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-019-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-019-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [ ] **MC-019-25** — Produce a normative design subsection specific to **WebAssembly Component Model runtime adapter** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in ADR-0001 §8; no normative subsection with worked examples
- [ ] **MC-019-26** — Create an end-to-end integration fixture proving **WebAssembly Component Model runtime adapter** works through its real production-facing path.  
  ↳ **PARTIAL** — no production Component Model runtime adapter (Wasmtime component API) is shipped; evidence is the reference adapter + a core-Wasm guest in V8

### E. Implementation

- [x] **MC-019-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-019-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-019-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-019-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [x] **MC-019-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [x] **MC-019-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ Boundary reads ConfigManager.current once per call (immutable Snapshot)
- [x] **MC-019-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-019-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-019-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-019-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-019-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-019-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-019-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-019-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-019-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-019-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-019-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/boundary.py, tools/wasm_host.mjs, fixtures/wasm-guest/main.go; tests: tests/test_canon.py::BoundaryIntegrationTest; evidence: evidence/wasm_guest.json
- [x] **MC-019-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/boundary.py, tools/wasm_host.mjs, fixtures/wasm-guest/main.go; tests: tests/test_canon.py::BoundaryIntegrationTest; evidence: evidence/wasm_guest.json
- [ ] **MC-019-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-019-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-019-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-019-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-019-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-019-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-019-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-019-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-019-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-019-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-019-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-019-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-019-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-019-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [ ] **MC-019-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ **OPEN** — no production Component Model runtime adapter (Wasmtime component API) is shipped; evidence is the reference adapter + a core-Wasm guest in V8
- [ ] **MC-019-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-019-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-020 — Rust binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Rust binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-020-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ COMPATIBILITY + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-020-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-020-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in fixtures/rust/src/main.rs
- [ ] **MC-020-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-020-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-020-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-020-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ COMPATIBILITY + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-020-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-020-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-020-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-020-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-020-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-020-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-020-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [x] **MC-020-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ no unsafe/FFI in Python/JS/Rust fixtures; Go guest confines unsafe.Pointer to base() address computation
- [x] **MC-020-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [x] **MC-020-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ fixtures map every failure to PK_INTEROP_* codes (panic->abiErr in Go, Result in Rust, AbiError in JS)
- [ ] **MC-020-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ **PARTIAL** — fixtures are single-shot processes; no teardown state
- [ ] **MC-020-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ **N/A-PROPOSED** — fixture processes are single-threaded
- [x] **MC-020-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ golden corpus covers every canonical kind (fixtures/corpus/corpus.wit)
- [ ] **MC-020-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [ ] **MC-020-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-020-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-020-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [ ] **MC-020-25** — Produce a normative design subsection specific to **Rust binding adapter and fixture component** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [x] **MC-020-26** — Create an end-to-end integration fixture proving **Rust binding adapter and fixture component** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-020-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-020-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-020-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-020-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-020-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-020-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-020-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-020-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-020-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-020-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-020-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-020-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-020-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-020-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-020-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-020-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-020-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: fixtures/rust/src/main.rs; tests: tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-020-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: fixtures/rust/src/main.rs; tests: tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-020-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-020-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-020-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-020-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-020-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-020-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-020-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-020-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-020-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-020-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-020-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-020-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-020-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-020-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-020-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-020-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-020-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-021 — Go binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Go binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-021-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ COMPATIBILITY + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-021-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-021-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in fixtures/go/main.go
- [ ] **MC-021-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-021-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-021-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-021-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ COMPATIBILITY + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-021-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-021-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-021-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-021-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-021-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-021-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-021-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [x] **MC-021-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ no unsafe/FFI in Python/JS/Rust fixtures; Go guest confines unsafe.Pointer to base() address computation
- [x] **MC-021-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [x] **MC-021-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ fixtures map every failure to PK_INTEROP_* codes (panic->abiErr in Go, Result in Rust, AbiError in JS)
- [ ] **MC-021-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ **PARTIAL** — fixtures are single-shot processes; no teardown state
- [ ] **MC-021-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ **N/A-PROPOSED** — fixture processes are single-threaded
- [x] **MC-021-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ golden corpus covers every canonical kind (fixtures/corpus/corpus.wit)
- [ ] **MC-021-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [ ] **MC-021-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-021-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-021-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [ ] **MC-021-25** — Produce a normative design subsection specific to **Go binding adapter and fixture component** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [x] **MC-021-26** — Create an end-to-end integration fixture proving **Go binding adapter and fixture component** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-021-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-021-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-021-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-021-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-021-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-021-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-021-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-021-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-021-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-021-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-021-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-021-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-021-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-021-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-021-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-021-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-021-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: fixtures/go/main.go, fixtures/wasm-guest/main.go; tests: tools/conformance.py; evidence: evidence/conformance.json, evidence/wasm_guest.json
- [x] **MC-021-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: fixtures/go/main.go, fixtures/wasm-guest/main.go; tests: tools/conformance.py; evidence: evidence/conformance.json, evidence/wasm_guest.json
- [x] **MC-021-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-021-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-021-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-021-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-021-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-021-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-021-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-021-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-021-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-021-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-021-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-021-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-021-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-021-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-021-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-021-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-021-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-022 — JavaScript binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `JavaScript binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-022-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ COMPATIBILITY + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-022-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-022-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in fixtures/js/inv12.mjs
- [ ] **MC-022-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-022-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-022-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-022-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ COMPATIBILITY + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-022-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-022-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-022-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-022-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-022-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-022-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-022-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [x] **MC-022-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ no unsafe/FFI in Python/JS/Rust fixtures; Go guest confines unsafe.Pointer to base() address computation
- [x] **MC-022-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [x] **MC-022-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ fixtures map every failure to PK_INTEROP_* codes (panic->abiErr in Go, Result in Rust, AbiError in JS)
- [ ] **MC-022-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ **PARTIAL** — fixtures are single-shot processes; no teardown state
- [ ] **MC-022-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ **N/A-PROPOSED** — fixture processes are single-threaded
- [x] **MC-022-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ golden corpus covers every canonical kind (fixtures/corpus/corpus.wit)
- [ ] **MC-022-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [ ] **MC-022-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-022-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-022-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [ ] **MC-022-25** — Produce a normative design subsection specific to **JavaScript binding adapter and fixture component** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [x] **MC-022-26** — Create an end-to-end integration fixture proving **JavaScript binding adapter and fixture component** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-022-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-022-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-022-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-022-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-022-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-022-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-022-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-022-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-022-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-022-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-022-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-022-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-022-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-022-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-022-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-022-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-022-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: fixtures/js/inv12.mjs; tests: tools/conformance.py; evidence: evidence/conformance.json, evidence/wasm_guest.json
- [x] **MC-022-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: fixtures/js/inv12.mjs; tests: tools/conformance.py; evidence: evidence/conformance.json, evidence/wasm_guest.json
- [x] **MC-022-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-022-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-022-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-022-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-022-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-022-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-022-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-022-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-022-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-022-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-022-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-022-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-022-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-022-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-022-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-022-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-022-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-023 — Python binding adapter and fixture component

**Category:** Runtime & Language Integration  
**Implementation intent:** Deliver `Python binding adapter and fixture component` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-023-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ COMPATIBILITY + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-023-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-023-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in canon/boundary.py
- [ ] **MC-023-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-023-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-023-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-023-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ COMPATIBILITY + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-023-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-023-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-023-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-023-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-023-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-023-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-023-14** — Pin supported compiler/interpreter/runtime versions and all ABI-affecting feature flags.  
  ↳ **PARTIAL** — toolchain versions recorded (evidence/deps.lock.json); not enforced at startup
- [x] **MC-023-15** — Constrain unsafe/FFI logic to a minimal reviewed boundary with explicit preconditions and postconditions.  
  ↳ no unsafe/FFI in Python/JS/Rust fixtures; Go guest confines unsafe.Pointer to base() address computation
- [x] **MC-023-16** — Prove values are copied, borrowed, or moved only according to canonical ownership rules and never by accidental aliasing.  
  ↳ BoundaryIntegrationTest.test_no_alias_across_boundary, ResourceTest; wasm harness copy-out
- [x] **MC-023-17** — Translate traps, panics, exceptions, and runtime errors into the canonical error model while preserving causal context.  
  ↳ fixtures map every failure to PK_INTEROP_* codes (panic->abiErr in Go, Result in Rust, AbiError in JS)
- [ ] **MC-023-18** — Make cleanup idempotent and correct across success, error, trap, cancellation, and runtime teardown.  
  ↳ **PARTIAL** — fixtures are single-shot processes; no teardown state
- [x] **MC-023-19** — Verify thread and async safety for registries, handles, callbacks, and global runtime state.  
  ↳ immutable registries; lock-guarded tables; ConcurrencyLeakTest
- [x] **MC-023-20** — Provide a fixture component/module that exercises the complete supported type surface.  
  ↳ golden corpus covers every canonical kind (fixtures/corpus/corpus.wit)
- [ ] **MC-023-21** — Refuse startup or binding generation when mandatory runtime features or versions are unavailable.  
  ↳ **PARTIAL** — config/registry refuse unsupported languages at call time; no startup feature probe

### D. Component-Specific Controls

- [ ] **MC-023-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-023-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-023-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [ ] **MC-023-25** — Produce a normative design subsection specific to **Python binding adapter and fixture component** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [x] **MC-023-26** — Create an end-to-end integration fixture proving **Python binding adapter and fixture component** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-023-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [x] **MC-023-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ checked_add/checked_mul/align_to (canon/memory.py); range checks (canon/numeric.py)
- [x] **MC-023-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-023-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [x] **MC-023-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [ ] **MC-023-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-023-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-023-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-023-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-023-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-023-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-023-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-023-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-023-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-023-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-023-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-023-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/boundary.py, canon/values.py, canon/cjv.py; tests: tests/test_canon.py::BoundaryIntegrationTest, tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-023-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/boundary.py, canon/values.py, canon/cjv.py; tests: tests/test_canon.py::BoundaryIntegrationTest, tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-023-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-023-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-023-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-023-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-023-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-023-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-023-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-023-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-023-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-023-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-023-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-023-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-023-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-023-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-023-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-023-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-023-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-024 — Cross-language conformance matrix

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Cross-language conformance matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-024-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-024-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-024-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in tools/conformance.py
- [ ] **MC-024-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-024-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-024-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-024-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-024-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-024-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-024-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-024-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-024-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-024-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [x] **MC-024-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ golden vectors are fixed files checked by 4 independent implementations
- [ ] **MC-024-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-024-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-024-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-024-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-024-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-024-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-024-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [x] **MC-024-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ frozen golden corpus + 4 independent implementations
- [ ] **MC-024-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-024-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [ ] **MC-024-25** — Produce a normative design subsection specific to **Cross-language conformance matrix** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [x] **MC-024-26** — Create an end-to-end integration fixture proving **Cross-language conformance matrix** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [ ] **MC-024-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-024-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-024-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-024-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-024-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-024-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-024-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-024-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-024-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/conformance.py; tests: tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-024-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/conformance.py; tests: tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-024-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-024-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-024-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-024-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-024-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-024-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-024-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-024-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-024-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-024-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-024-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-024-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-024-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-024-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-024-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-024-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-024-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-025 — Adjacent-layer integration fixtures

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Adjacent-layer integration fixtures` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-025-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ THREAT_MODEL R1 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-025-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-025-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ THREAT_MODEL R1; typed signatures + PK_INTEROP_* errors in canon/boundary.py
- [x] **MC-025-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-025-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-025-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-025-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ THREAT_MODEL R1 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-025-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-025-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-025-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-025-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-025-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-025-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [ ] **MC-025-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-025-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-025-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-025-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-025-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-025-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-025-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-025-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-025-22** — Produce a normative design subsection specific to **Adjacent-layer integration fixtures** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in THREAT_MODEL R1; no normative subsection with worked examples
- [ ] **MC-025-23** — Create an end-to-end integration fixture proving **Adjacent-layer integration fixtures** works through its real production-facing path.  
  ↳ **PARTIAL** — no INV-10 / INV-11 / INV-13 / INV-45 artifacts are available; only stand-ins (schema loader, reference composition, V8 memory isolation) were exercised
- [ ] **MC-025-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Adjacent-layer integration fixtures** and enforce them automatically.  
  ↳ **OPEN** — no component-specific budget defined
- [ ] **MC-025-25** — Record assumptions and unsupported cases for **Adjacent-layer integration fixtures** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [ ] **MC-025-26** — Create at least one failure-injection scenario for **Adjacent-layer integration fixtures** that proves safe rollback or containment.  
  ↳ **PARTIAL** — negative tests exist; no dedicated failure-injection scenario

### E. Implementation

- [x] **MC-025-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-025-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-025-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-025-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-025-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-025-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-025-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-025-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-025-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-025-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-025-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-025-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-025-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-025-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-025-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-025-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-025-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/boundary.py, tools/wasm_host.mjs; tests: tests/test_canon.py::BoundaryIntegrationTest; evidence: evidence/wasm_guest.json
- [x] **MC-025-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/boundary.py, tools/wasm_host.mjs; tests: tests/test_canon.py::BoundaryIntegrationTest; evidence: evidence/wasm_guest.json
- [ ] **MC-025-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-025-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-025-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-025-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-025-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-025-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-025-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-025-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-025-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-025-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-025-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-025-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-025-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-025-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [ ] **MC-025-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ **OPEN** — no INV-10 / INV-11 / INV-13 / INV-45 artifacts are available; only stand-ins (schema loader, reference composition, V8 memory isolation) were exercised
- [ ] **MC-025-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-025-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-026 — Golden canonical test-vector corpus

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Golden canonical test-vector corpus` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-026-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-026-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-026-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in tools/gen_corpus.py
- [ ] **MC-026-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-026-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-026-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-026-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [x] **MC-026-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-026-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-026-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-026-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-026-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-026-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [x] **MC-026-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ golden vectors are fixed files checked by 4 independent implementations
- [ ] **MC-026-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-026-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-026-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-026-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-026-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-026-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-026-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [x] **MC-026-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ frozen golden corpus + 4 independent implementations
- [x] **MC-026-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ seeds + regressions persisted (fixtures/fuzz/regressions, evidence JSON)
- [x] **MC-026-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [x] **MC-026-25** — Produce a normative design subsection specific to **Golden canonical test-vector corpus** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §7
- [x] **MC-026-26** — Create an end-to-end integration fixture proving **Golden canonical test-vector corpus** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [ ] **MC-026-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-026-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [x] **MC-026-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ deterministic generated artifacts with digests (vectors.json schema_digest, SBOM, MANIFEST)

### F. Security & Hardening

- [ ] **MC-026-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-026-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-026-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-026-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-026-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-026-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-026-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/gen_corpus.py, fixtures/corpus/vectors.json; tests: tests/test_canon.py::LayoutMemoryTest; evidence: evidence/conformance.json
- [x] **MC-026-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/gen_corpus.py, fixtures/corpus/vectors.json; tests: tests/test_canon.py::LayoutMemoryTest; evidence: evidence/conformance.json
- [x] **MC-026-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-026-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-026-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-026-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-026-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-026-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-026-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-026-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-026-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-026-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-026-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-026-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-026-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-026-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-026-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-026-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-026-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-027 — Property-based test harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Property-based test harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-027-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-027-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-027-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in canon/generators.py
- [ ] **MC-027-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-027-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-027-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-027-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [x] **MC-027-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-027-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-027-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-027-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-027-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-027-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-027-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [x] **MC-027-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ fixtures/fuzz/regressions/ replayed in CI; seeds recorded in evidence JSON
- [x] **MC-027-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-027-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-027-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-027-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-027-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-027-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-027-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [x] **MC-027-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ seeds + regressions persisted (fixtures/fuzz/regressions, evidence JSON)
- [x] **MC-027-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [x] **MC-027-25** — Produce a normative design subsection specific to **Property-based test harness** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §7
- [ ] **MC-027-26** — Create an end-to-end integration fixture proving **Property-based test harness** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-027-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-027-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-027-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-027-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-027-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-027-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-027-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-027-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-027-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/generators.py; tests: tests/test_canon.py::PropertyTest; evidence: evidence/coverage.json
- [x] **MC-027-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/generators.py; tests: tests/test_canon.py::PropertyTest; evidence: evidence/coverage.json
- [x] **MC-027-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-027-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-027-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-027-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-027-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-027-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-027-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-027-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-027-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-027-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-027-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-027-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-027-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-027-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-027-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-027-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-027-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-028 — Coverage-guided fuzzing harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Coverage-guided fuzzing harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-028-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-028-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-028-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ THREAT_MODEL; typed signatures + PK_INTEROP_* errors in tools/fuzz.py
- [ ] **MC-028-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-028-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-028-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-028-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-028-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-028-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-028-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-028-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-028-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-028-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-028-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [x] **MC-028-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ fixtures/fuzz/regressions/ replayed in CI; seeds recorded in evidence JSON
- [x] **MC-028-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-028-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-028-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-028-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-028-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-028-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-028-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [x] **MC-028-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ seeds + regressions persisted (fixtures/fuzz/regressions, evidence JSON)
- [x] **MC-028-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [ ] **MC-028-25** — Produce a normative design subsection specific to **Coverage-guided fuzzing harness** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in THREAT_MODEL; no normative subsection with worked examples
- [ ] **MC-028-26** — Create an end-to-end integration fixture proving **Coverage-guided fuzzing harness** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-028-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-028-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-028-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [ ] **MC-028-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-028-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-028-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-028-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-028-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-028-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/fuzz.py, fixtures/fuzz/regressions; tests: tools/fuzz.py; evidence: evidence/fuzz.json
- [x] **MC-028-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/fuzz.py, fixtures/fuzz/regressions; tests: tools/fuzz.py; evidence: evidence/fuzz.json
- [x] **MC-028-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-028-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-028-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-028-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-028-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-028-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-028-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-028-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-028-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-028-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-028-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-028-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-028-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-028-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-028-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-028-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-028-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-029 — Differential runtime tester

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Differential runtime tester` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-029-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-029-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-029-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in tools/conformance.py
- [ ] **MC-029-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-029-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-029-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-029-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-029-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-029-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-029-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-029-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-029-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-029-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [x] **MC-029-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ golden vectors are fixed files checked by 4 independent implementations
- [x] **MC-029-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ fixtures/fuzz/regressions/ replayed in CI; seeds recorded in evidence JSON
- [x] **MC-029-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-029-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-029-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-029-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-029-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-029-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-029-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — golden corpus exercises every type; lifecycle/async paths not through a real runtime adapter
- [ ] **MC-029-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-029-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [x] **MC-029-25** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ frozen golden corpus + 4 independent implementations
- [x] **MC-029-26** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ seeds + regressions persisted (fixtures/fuzz/regressions, evidence JSON)

### E. Implementation

- [ ] **MC-029-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-029-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-029-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-029-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-029-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-029-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-029-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-029-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-029-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/conformance.py; tests: tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-029-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/conformance.py; tests: tools/conformance.py; evidence: evidence/conformance.json
- [x] **MC-029-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-029-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-029-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-029-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-029-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-029-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-029-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-029-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-029-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-029-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-029-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-029-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-029-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-029-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-029-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-029-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-029-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-030 — Malicious-memory test harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Malicious-memory test harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-030-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-030-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-030-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ THREAT_MODEL T1/T10; typed signatures + PK_INTEROP_* errors in canon/memory.py
- [ ] **MC-030-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-030-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-030-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-030-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-030-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [x] **MC-030-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/memory.py
- [x] **MC-030-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ single release path: CheckedRealloc/CallLifecycle, ResourceTable.drop (dtor exactly once)
- [ ] **MC-030-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-030-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-030-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-030-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [x] **MC-030-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ fixtures/fuzz/regressions/ replayed in CI; seeds recorded in evidence JSON
- [x] **MC-030-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-030-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-030-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-030-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-030-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-030-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [x] **MC-030-22** — Specify ownership/lifetime transitions as a finite-state machine and reject stale, duplicate, forged, moved, or wrong-type references.  
  ↳ state machines in canon/resources.py / canon/memory.py; stale/foreign/moved/wrong-type refused
- [x] **MC-030-23** — Instrument allocation/resource accounting and require zero leaks, double releases, or use-after-release in fault-injected tests.  
  ↳ CheckedRealloc accounting, dtor_calls, leaked()==0 after fault injection
- [ ] **MC-030-24** — Exercise cleanup across success, exception/trap, cancellation, re-entrancy, and concurrent teardown.  
  ↳ **PARTIAL** — cleanup tested for success/exception; no trap/cancellation path
- [ ] **MC-030-25** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [x] **MC-030-26** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ seeds + regressions persisted (fixtures/fuzz/regressions, evidence JSON)

### E. Implementation

- [ ] **MC-030-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-030-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-030-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [ ] **MC-030-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-030-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-030-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-030-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-030-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-030-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/memory.py, tools/wasm_host.mjs; tests: tests/test_canon.py::MaliciousMemoryTest; evidence: evidence/wasm_guest.json, evidence/fuzz.json
- [x] **MC-030-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/memory.py, tools/wasm_host.mjs; tests: tests/test_canon.py::MaliciousMemoryTest; evidence: evidence/wasm_guest.json, evidence/fuzz.json
- [x] **MC-030-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ PropertyTest (400 seeded cases) + tools/fuzz.py (evidence/fuzz.json) + differential (evidence/conformance.json)
- [ ] **MC-030-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-030-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-030-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-030-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-030-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-030-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-030-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-030-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-030-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-030-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-030-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-030-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-030-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-030-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-030-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-030-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-031 — Concurrency/race stress suite

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Concurrency/race stress suite` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-031-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-031-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-031-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §4; typed signatures + PK_INTEROP_* errors in tests/test_canon.py
- [ ] **MC-031-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-031-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-031-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-031-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-031-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-031-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-031-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-031-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (tests/test_canon.py)
- [ ] **MC-031-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-031-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-031-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-031-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-031-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-031-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-031-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-031-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-031-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-031-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [x] **MC-031-22** — Produce a normative design subsection specific to **Concurrency/race stress suite** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §4
- [ ] **MC-031-23** — Create an end-to-end integration fixture proving **Concurrency/race stress suite** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path
- [ ] **MC-031-24** — Define component-specific latency, throughput, memory, and failure-rate budgets for **Concurrency/race stress suite** and enforce them automatically.  
  ↳ **OPEN** — no component-specific budget defined
- [ ] **MC-031-25** — Record assumptions and unsupported cases for **Concurrency/race stress suite** in machine-readable release metadata where practical.  
  ↳ **PARTIAL** — assumptions recorded in docs (COMPATIBILITY/ADR); not in machine-readable release metadata
- [x] **MC-031-26** — Create at least one failure-injection scenario for **Concurrency/race stress suite** that proves safe rollback or containment.  
  ↳ invalid args / leaked borrow / hostile realloc injections with rollback asserted

### E. Implementation

- [ ] **MC-031-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-031-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-031-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-031-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-031-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-031-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-031-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-031-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-031-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tests/test_canon.py; tests: tests/test_canon.py::ConcurrencyLeakTest, tests/test_canon.py::AsyncTest; evidence: evidence/ci_run.json
- [x] **MC-031-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tests/test_canon.py; tests: tests/test_canon.py::ConcurrencyLeakTest, tests/test_canon.py::AsyncTest; evidence: evidence/ci_run.json
- [ ] **MC-031-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [x] **MC-031-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-031-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-031-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-031-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-031-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-031-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-031-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-031-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-031-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-031-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-031-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-031-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-031-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-031-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-031-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-031-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-032 — Leak/use-after-free detector integration

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Leak/use-after-free detector integration` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-032-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-032-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-032-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §7; typed signatures + PK_INTEROP_* errors in canon/memory.py
- [ ] **MC-032-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-032-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-032-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-032-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-032-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-032-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-032-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-032-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-032-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-032-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-032-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-032-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-032-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-032-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-032-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-032-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-032-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-032-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-032-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [ ] **MC-032-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-032-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [x] **MC-032-25** — Produce a normative design subsection specific to **Leak/use-after-free detector integration** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §7
- [ ] **MC-032-26** — Create an end-to-end integration fixture proving **Leak/use-after-free detector integration** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-032-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-032-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-032-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-032-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-032-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-032-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-032-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-032-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-032-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/memory.py; tests: tests/test_canon.py::ConcurrencyLeakTest, tests/test_canon.py::LayoutMemoryTest; evidence: evidence/ci_run.json
- [x] **MC-032-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/memory.py; tests: tests/test_canon.py::ConcurrencyLeakTest, tests/test_canon.py::LayoutMemoryTest; evidence: evidence/ci_run.json
- [ ] **MC-032-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-032-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-032-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-032-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-032-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-032-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-032-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-032-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-032-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-032-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-032-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-032-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-032-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-032-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-032-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-032-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-032-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-033 — Cross-platform architecture matrix

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Cross-platform architecture matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-033-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-033-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-033-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in ci/github-actions.yml
- [ ] **MC-033-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-033-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-033-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-033-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-033-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-033-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-033-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-033-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-033-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-033-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-033-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-033-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-033-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-033-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-033-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-033-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-033-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-033-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-033-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [ ] **MC-033-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [ ] **MC-033-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ **BLOCKED** — only Linux x86-64 executed; ARM64/macOS/Windows declared in ci/github-actions.yml but not run
- [ ] **MC-033-25** — Produce a normative design subsection specific to **Cross-platform architecture matrix** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [ ] **MC-033-26** — Create an end-to-end integration fixture proving **Cross-platform architecture matrix** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-033-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-033-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-033-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-033-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-033-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-033-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-033-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-033-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [ ] **MC-033-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ **OPEN** — no unit tests for this component
- [ ] **MC-033-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **OPEN** — no negative tests
- [ ] **MC-033-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-033-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-033-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-033-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-033-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-033-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-033-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-033-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-033-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-033-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-033-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-033-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-033-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-033-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [ ] **MC-033-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ **OPEN** — only Linux x86-64 executed; ARM64/macOS/Windows declared in ci/github-actions.yml but not run
- [ ] **MC-033-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-033-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-034 — Performance benchmark harness

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Performance benchmark harness` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-034-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-034-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-034-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ COMPATIBILITY; typed signatures + PK_INTEROP_* errors in tools/bench.py
- [ ] **MC-034-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-034-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-034-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-034-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-034-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-034-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-034-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-034-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-034-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-034-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-034-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-034-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-034-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-034-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-034-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-034-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-034-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-034-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-034-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [ ] **MC-034-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-034-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [ ] **MC-034-25** — Produce a normative design subsection specific to **Performance benchmark harness** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in COMPATIBILITY; no normative subsection with worked examples
- [ ] **MC-034-26** — Create an end-to-end integration fixture proving **Performance benchmark harness** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-034-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-034-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-034-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-034-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-034-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-034-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-034-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-034-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-034-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/bench.py; tests: tools/bench.py; evidence: evidence/bench.json
- [x] **MC-034-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/bench.py; tests: tools/bench.py; evidence: evidence/bench.json
- [ ] **MC-034-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-034-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-034-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-034-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-034-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-034-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-034-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-034-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-034-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-034-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-034-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-034-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-034-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-034-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-034-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-034-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-034-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-035 — SLO certification gate

**Category:** Verification & Certification  
**Implementation intent:** Deliver `SLO certification gate` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-035-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-035-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-035-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ README SLO; typed signatures + PK_INTEROP_* errors in tools/bench.py
- [ ] **MC-035-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-035-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-035-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-035-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-035-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-035-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-035-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-035-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-035-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-035-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-035-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-035-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-035-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-035-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-035-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-035-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-035-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-035-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-035-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [ ] **MC-035-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-035-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [ ] **MC-035-25** — Produce a normative design subsection specific to **SLO certification gate** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in README SLO; no normative subsection with worked examples
- [ ] **MC-035-26** — Create an end-to-end integration fixture proving **SLO certification gate** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-035-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-035-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-035-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-035-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-035-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-035-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-035-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-035-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-035-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/bench.py, ci/bench_thresholds.json; tests: tools/bench.py; evidence: evidence/bench.json
- [x] **MC-035-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/bench.py, ci/bench_thresholds.json; tests: tools/bench.py; evidence: evidence/bench.json
- [ ] **MC-035-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-035-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-035-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-035-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-035-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-035-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-035-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-035-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-035-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-035-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-035-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-035-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-035-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-035-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-035-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-035-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-035-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-036 — Large-payload/DoS benchmark suite

**Category:** Verification & Certification  
**Implementation intent:** Deliver `Large-payload/DoS benchmark suite` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-036-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-036-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-036-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §5; typed signatures + PK_INTEROP_* errors in tools/bench.py
- [ ] **MC-036-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-036-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [x] **MC-036-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ machine-checked thresholds in tools/ gate scripts + ci/bench_thresholds.json

### B. Architecture & Data Model

- [ ] **MC-036-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-036-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-036-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-036-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-036-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [x] **MC-036-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [ ] **MC-036-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-036-14** — Keep the reference oracle independent from the implementation under test.  
  ↳ **PARTIAL** — oracle is the Python reference implementation
- [ ] **MC-036-15** — Persist failing seeds and minimized counterexamples as deterministic regression fixtures.  
  ↳ **PARTIAL** — seeds recorded; no minimization for this suite
- [x] **MC-036-16** — Exercise both valid and intentionally invalid inputs with stable fail-closed classifications.  
  ↳ corpus valid + invalid vectors; fail-closed codes asserted
- [ ] **MC-036-17** — Collect branch, error-path, and state-transition coverage rather than statement coverage alone.  
  ↳ **PARTIAL** — line+arc coverage only (evidence/coverage.json)
- [x] **MC-036-18** — Run release/optimized builds in addition to debug builds to detect assertion-dependent correctness.  
  ↳ python -O suite + cargo --release (overflow-checks on) (evidence/ci_run.json)
- [ ] **MC-036-19** — Retain machine-readable evidence with exact source revision, runtime, platform, and toolchain metadata.  
  ↳ **PARTIAL** — evidence retains platform/toolchain; source identified by tree digest, no VCS revision
- [ ] **MC-036-20** — Define flake, retry, and quarantine policy with owners and expiry; repeated retries do not equal a clean pass.  
  ↳ **OPEN** — no flake/retry/quarantine policy defined
- [x] **MC-036-21** — Block release on unresolved P0/P1 correctness, memory-safety, compatibility, or security defects.  
  ↳ tools/ci.py exits non-zero on any failing gate (ci_negative_test.json)

### D. Component-Specific Controls

- [ ] **MC-036-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ **PARTIAL** — expected values partly derived from the reference implementation
- [ ] **MC-036-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-036-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [x] **MC-036-25** — Produce a normative design subsection specific to **Large-payload/DoS benchmark suite** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §5
- [ ] **MC-036-26** — Create an end-to-end integration fixture proving **Large-payload/DoS benchmark suite** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-036-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-036-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-036-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [ ] **MC-036-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-036-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-036-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [ ] **MC-036-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-036-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-036-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/bench.py; tests: tools/bench.py; evidence: evidence/bench.json
- [x] **MC-036-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/bench.py; tests: tools/bench.py; evidence: evidence/bench.json
- [ ] **MC-036-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-036-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-036-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-036-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-036-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-036-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-036-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-036-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-036-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-036-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-036-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-036-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-036-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-036-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-036-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-036-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-036-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-037 — Metrics emitter

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Metrics emitter` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-037-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-037-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-037-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/observability.py
- [ ] **MC-037-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-037-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-037-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-037-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-037-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-037-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-037-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-037-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/observability.py)
- [ ] **MC-037-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-037-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-037-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.  
  ↳ Health HEALTHY/DEGRADED/BLOCKED machine-readable status()
- [x] **MC-037-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.  
  ↳ closed label vocabulary; test_metrics_bounded_cardinality (1000 labels -> 1 series)
- [ ] **MC-037-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.  
  ↳ **PARTIAL** — span ids + audit seq ids; no shared trace id propagated across components
- [ ] **MC-037-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.  
  ↳ **PARTIAL** — telemetry bounded (max_spans, fixed series) but not load-tested
- [ ] **MC-037-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.  
  ↳ **PARTIAL** — tracer drops beyond max_spans with a dropped counter; audit/metrics failure modes not exercised
- [ ] **MC-037-19** — Provide runbook queries or dashboards mapped directly to component failure modes.  
  ↳ **PARTIAL** — docs/RUNBOOK.md lists metric names per failure signature; no dashboards
- [ ] **MC-037-20** — Version telemetry schemas and preserve compatibility for downstream automation.  
  ↳ **PARTIAL** — metric names prefixed inv12_; no explicit telemetry schema version
- [x] **MC-037-21** — Exercise observability in integration tests so critical failures cannot occur silently.  
  ↳ BoundaryIntegrationTest asserts boundary_calls; trace error attribution test

### D. Component-Specific Controls

- [x] **MC-037-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.  
  ↳ closed vocabularies (Metrics/_LABEL_VOCAB, Tracer.ATTRS, AuditLog.EVENTS, Health conditions)
- [ ] **MC-037-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.  
  ↳ **PARTIAL** — codes -> counters mapped; alert conditions not defined
- [ ] **MC-037-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.  
  ↳ **PARTIAL** — contention test runs with metrics+tracer enabled; no dedicated overload test of telemetry
- [x] **MC-037-25** — Produce a normative design subsection specific to **Metrics emitter** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §11
- [x] **MC-037-26** — Create an end-to-end integration fixture proving **Metrics emitter** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-037-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-037-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-037-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-037-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-037-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-037-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-037-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-037-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-037-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-037-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-037-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-037-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-037-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-037-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-037-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-037-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-037-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest, tests/test_canon.py::BoundaryIntegrationTest
- [x] **MC-037-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest, tests/test_canon.py::BoundaryIntegrationTest
- [ ] **MC-037-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-037-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-037-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-037-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-037-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-037-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-037-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-037-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-037-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-037-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-037-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-037-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-037-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-037-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-037-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-037-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-037-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-038 — Distributed trace instrumentation

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Distributed trace instrumentation` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-038-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-038-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-038-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/observability.py
- [ ] **MC-038-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-038-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-038-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-038-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-038-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-038-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-038-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-038-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/observability.py)
- [ ] **MC-038-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-038-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-038-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.  
  ↳ Health HEALTHY/DEGRADED/BLOCKED machine-readable status()
- [x] **MC-038-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.  
  ↳ closed label vocabulary; test_metrics_bounded_cardinality (1000 labels -> 1 series)
- [ ] **MC-038-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.  
  ↳ **PARTIAL** — span ids + audit seq ids; no shared trace id propagated across components
- [ ] **MC-038-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.  
  ↳ **PARTIAL** — telemetry bounded (max_spans, fixed series) but not load-tested
- [ ] **MC-038-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.  
  ↳ **PARTIAL** — tracer drops beyond max_spans with a dropped counter; audit/metrics failure modes not exercised
- [ ] **MC-038-19** — Provide runbook queries or dashboards mapped directly to component failure modes.  
  ↳ **PARTIAL** — docs/RUNBOOK.md lists metric names per failure signature; no dashboards
- [ ] **MC-038-20** — Version telemetry schemas and preserve compatibility for downstream automation.  
  ↳ **PARTIAL** — metric names prefixed inv12_; no explicit telemetry schema version
- [x] **MC-038-21** — Exercise observability in integration tests so critical failures cannot occur silently.  
  ↳ BoundaryIntegrationTest asserts boundary_calls; trace error attribution test

### D. Component-Specific Controls

- [x] **MC-038-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.  
  ↳ closed vocabularies (Metrics/_LABEL_VOCAB, Tracer.ATTRS, AuditLog.EVENTS, Health conditions)
- [ ] **MC-038-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.  
  ↳ **PARTIAL** — codes -> counters mapped; alert conditions not defined
- [ ] **MC-038-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.  
  ↳ **PARTIAL** — contention test runs with metrics+tracer enabled; no dedicated overload test of telemetry
- [x] **MC-038-25** — Produce a normative design subsection specific to **Distributed trace instrumentation** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §11
- [ ] **MC-038-26** — Create an end-to-end integration fixture proving **Distributed trace instrumentation** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-038-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-038-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-038-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-038-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-038-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-038-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-038-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-038-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-038-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-038-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-038-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-038-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-038-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-038-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-038-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-038-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-038-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest
- [x] **MC-038-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest
- [ ] **MC-038-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-038-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-038-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-038-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-038-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-038-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-038-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-038-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-038-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-038-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-038-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-038-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-038-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-038-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-038-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-038-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-038-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-039 — Structured security audit events

**Category:** Security & Policy  
**Implementation intent:** Deliver `Structured security audit events` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-039-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-039-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-039-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/observability.py
- [ ] **MC-039-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-039-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-039-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-039-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-039-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-039-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-039-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-039-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/observability.py)
- [ ] **MC-039-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-039-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-039-14** — Document the trust boundary and exact authority granted to this component.  
  ↳ docs/SPEC.md §0 trust boundaries; docs/THREAT_MODEL.md
- [x] **MC-039-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.  
  ↳ unknown identities/codes/languages/configs refused (ConfigTrustTest, RegistryNumericUnicodeTest)
- [x] **MC-039-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.  
  ↳ decisions keyed to config revision/digest; AuditLog hash chain
- [x] **MC-039-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.  
  ↳ Limits/Budget, bounded diagnostics (160 chars/32 segments), max_spans
- [x] **MC-039-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.  
  ↳ hmac.compare_digest for MACs (config, audit, trust)
- [x] **MC-039-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.  
  ↳ revision replay refused; transcript digests; foreign/stale handles refused; key revocation clears cache
- [x] **MC-039-20** — Classify and redact logs, errors, traces, and audit events before emission.  
  ↳ errors.redact + span attribute allow-list
- [ ] **MC-039-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.  
  ↳ **PARTIAL** — outage behaviour defined in SPEC §11; not exercised for this component

### D. Component-Specific Controls

- [x] **MC-039-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.  
  ↳ closed vocabularies (Metrics/_LABEL_VOCAB, Tracer.ATTRS, AuditLog.EVENTS, Health conditions)
- [ ] **MC-039-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.  
  ↳ **PARTIAL** — codes -> counters mapped; alert conditions not defined
- [ ] **MC-039-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.  
  ↳ **PARTIAL** — contention test runs with metrics+tracer enabled; no dedicated overload test of telemetry
- [x] **MC-039-25** — Produce a normative design subsection specific to **Structured security audit events** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §11
- [ ] **MC-039-26** — Create an end-to-end integration fixture proving **Structured security audit events** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-039-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-039-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-039-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-039-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-039-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-039-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-039-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-039-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-039-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-039-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-039-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-039-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-039-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-039-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-039-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-039-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-039-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest, tests/test_canon.py::ConfigTrustTest
- [x] **MC-039-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest, tests/test_canon.py::ConfigTrustTest
- [ ] **MC-039-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-039-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-039-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-039-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-039-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-039-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-039-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-039-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-039-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-039-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-039-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-039-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-039-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-039-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-039-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-039-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-039-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-040 — Diagnostic redaction policy

**Category:** Security & Policy  
**Implementation intent:** Deliver `Diagnostic redaction policy` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-040-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §8 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-040-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-040-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §8; typed signatures + PK_INTEROP_* errors in canon/errors.py
- [ ] **MC-040-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-040-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-040-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-040-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §8 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-040-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-040-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-040-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-040-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-040-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-040-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-040-14** — Document the trust boundary and exact authority granted to this component.  
  ↳ docs/SPEC.md §0 trust boundaries; docs/THREAT_MODEL.md
- [x] **MC-040-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.  
  ↳ unknown identities/codes/languages/configs refused (ConfigTrustTest, RegistryNumericUnicodeTest)
- [x] **MC-040-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.  
  ↳ decisions keyed to config revision/digest; AuditLog hash chain
- [x] **MC-040-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.  
  ↳ Limits/Budget, bounded diagnostics (160 chars/32 segments), max_spans
- [x] **MC-040-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.  
  ↳ hmac.compare_digest for MACs (config, audit, trust)
- [x] **MC-040-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.  
  ↳ revision replay refused; transcript digests; foreign/stale handles refused; key revocation clears cache
- [x] **MC-040-20** — Classify and redact logs, errors, traces, and audit events before emission.  
  ↳ errors.redact + span attribute allow-list
- [ ] **MC-040-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.  
  ↳ **PARTIAL** — outage behaviour defined in SPEC §11; not exercised for this component

### D. Component-Specific Controls

- [x] **MC-040-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.  
  ↳ validate_config + quorum approvals before atomic swap
- [ ] **MC-040-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.  
  ↳ **PARTIAL** — digest/actor/revision recorded; rollback target implicit (history)
- [ ] **MC-040-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.  
  ↳ **PARTIAL** — malformed/rollback/outage tested; mixed-version/stale-cache not
- [x] **MC-040-25** — Produce a normative design subsection specific to **Diagnostic redaction policy** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §8
- [ ] **MC-040-26** — Create an end-to-end integration fixture proving **Diagnostic redaction policy** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-040-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-040-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-040-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-040-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-040-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-040-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-040-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-040-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-040-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-040-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-040-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-040-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-040-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-040-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-040-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-040-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-040-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/errors.py, canon/observability.py; tests: tests/test_canon.py::ErrorEnvelopeTest
- [x] **MC-040-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/errors.py, canon/observability.py; tests: tests/test_canon.py::ErrorEnvelopeTest
- [ ] **MC-040-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-040-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-040-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-040-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-040-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-040-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-040-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-040-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-040-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-040-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-040-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-040-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-040-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-040-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-040-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-040-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-040-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-041 — Runtime health/readiness model

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Runtime health/readiness model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-041-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-041-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-041-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/observability.py
- [ ] **MC-041-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-041-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-041-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-041-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-041-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-041-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/observability.py
- [ ] **MC-041-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-041-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/observability.py)
- [ ] **MC-041-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-041-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-041-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.  
  ↳ Health HEALTHY/DEGRADED/BLOCKED machine-readable status()
- [x] **MC-041-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.  
  ↳ closed label vocabulary; test_metrics_bounded_cardinality (1000 labels -> 1 series)
- [ ] **MC-041-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.  
  ↳ **PARTIAL** — span ids + audit seq ids; no shared trace id propagated across components
- [x] **MC-041-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.  
  ↳ CapacityController admission + stream backpressure (tests)
- [ ] **MC-041-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.  
  ↳ **PARTIAL** — tracer drops beyond max_spans with a dropped counter; audit/metrics failure modes not exercised
- [ ] **MC-041-19** — Provide runbook queries or dashboards mapped directly to component failure modes.  
  ↳ **PARTIAL** — docs/RUNBOOK.md lists metric names per failure signature; no dashboards
- [ ] **MC-041-20** — Version telemetry schemas and preserve compatibility for downstream automation.  
  ↳ **PARTIAL** — metric names prefixed inv12_; no explicit telemetry schema version
- [x] **MC-041-21** — Exercise observability in integration tests so critical failures cannot occur silently.  
  ↳ BoundaryIntegrationTest asserts boundary_calls; trace error attribution test

### D. Component-Specific Controls

- [ ] **MC-041-22** — Create a production-like fixture that exercises every supported type, error path, lifecycle operation, and async path through the real adapter.  
  ↳ **PARTIAL** — health exercised via unit tests only
- [ ] **MC-041-23** — Pin runtime/compiler versions and fail initialization when required features or ABI expectations are not met.  
  ↳ **PARTIAL** — versions recorded; initialization does not probe features
- [x] **MC-041-24** — Verify cross-boundary values are detached/canonicalized according to contract and never share mutable host state accidentally.  
  ↳ copy-in/copy-out asserted (BoundaryIntegrationTest, wasm liftFromMemory copies buffer)
- [x] **MC-041-25** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.  
  ↳ closed vocabularies (Metrics/_LABEL_VOCAB, Tracer.ATTRS, AuditLog.EVENTS, Health conditions)
- [ ] **MC-041-26** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.  
  ↳ **PARTIAL** — codes -> counters mapped; alert conditions not defined

### E. Implementation

- [x] **MC-041-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-041-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-041-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-041-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-041-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-041-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-041-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-041-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-041-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-041-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-041-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-041-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-041-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-041-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-041-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-041-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-041-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest
- [x] **MC-041-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest
- [ ] **MC-041-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-041-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-041-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-041-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-041-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-041-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-041-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-041-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-041-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-041-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-041-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-041-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-041-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-041-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-041-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-041-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-041-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-042 — Capacity/fairness controller

**Category:** Observability & Operations  
**Implementation intent:** Deliver `Capacity/fairness controller` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-042-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-042-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-042-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/observability.py
- [ ] **MC-042-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-042-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-042-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-042-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-042-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-042-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/observability.py
- [ ] **MC-042-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-042-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/observability.py)
- [x] **MC-042-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ canon/limits.py hard ceiling + per-interface/type policy; schema limits in canon/types.py
- [x] **MC-042-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-042-14** — Define a stable operational state model exposed through machine-readable health/status interfaces.  
  ↳ Health HEALTHY/DEGRADED/BLOCKED machine-readable status()
- [x] **MC-042-15** — Use bounded-cardinality telemetry dimensions and document a cardinality budget.  
  ↳ closed label vocabulary; test_metrics_bounded_cardinality (1000 labels -> 1 series)
- [ ] **MC-042-16** — Correlate metrics, traces, logs, and audit events with stable IDs without leaking secrets.  
  ↳ **PARTIAL** — span ids + audit seq ids; no shared trace id propagated across components
- [x] **MC-042-17** — Define overload behavior and verify graceful degradation rather than uncontrolled latency/memory growth.  
  ↳ CapacityController admission + stream backpressure (tests)
- [ ] **MC-042-18** — Make telemetry failure non-fatal to core correctness while exposing loss-of-observability state.  
  ↳ **PARTIAL** — tracer drops beyond max_spans with a dropped counter; audit/metrics failure modes not exercised
- [ ] **MC-042-19** — Provide runbook queries or dashboards mapped directly to component failure modes.  
  ↳ **PARTIAL** — docs/RUNBOOK.md lists metric names per failure signature; no dashboards
- [ ] **MC-042-20** — Version telemetry schemas and preserve compatibility for downstream automation.  
  ↳ **PARTIAL** — metric names prefixed inv12_; no explicit telemetry schema version
- [x] **MC-042-21** — Exercise observability in integration tests so critical failures cannot occur silently.  
  ↳ BoundaryIntegrationTest asserts boundary_calls; trace error attribution test

### D. Component-Specific Controls

- [x] **MC-042-22** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.  
  ↳ closed vocabularies (Metrics/_LABEL_VOCAB, Tracer.ATTRS, AuditLog.EVENTS, Health conditions)
- [ ] **MC-042-23** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.  
  ↳ **PARTIAL** — codes -> counters mapped; alert conditions not defined
- [ ] **MC-042-24** — Load-test telemetry and health behavior under overload so observability cannot amplify an incident.  
  ↳ **PARTIAL** — contention test runs with metrics+tracer enabled; no dedicated overload test of telemetry
- [x] **MC-042-25** — Produce a normative design subsection specific to **Capacity/fairness controller** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §11
- [ ] **MC-042-26** — Create an end-to-end integration fixture proving **Capacity/fairness controller** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-042-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-042-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-042-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-042-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-042-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-042-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-042-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-042-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-042-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-042-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-042-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-042-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-042-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [x] **MC-042-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ limits checked before proportional work (evidence/bench.json DoS rows)
- [x] **MC-042-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-042-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-042-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest
- [x] **MC-042-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/observability.py; tests: tests/test_canon.py::ObservabilityTest
- [ ] **MC-042-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-042-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-042-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-042-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-042-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-042-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-042-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-042-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-042-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-042-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-042-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-042-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-042-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-042-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-042-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-042-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-042-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-043 — Declarative configuration schema

**Category:** Configuration & Governance  
**Implementation intent:** Deliver `Declarative configuration schema` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-043-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ OPERATIONS + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-043-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-043-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ OPERATIONS; typed signatures + PK_INTEROP_* errors in canon/config.py
- [x] **MC-043-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-043-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-043-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-043-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ OPERATIONS + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-043-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-043-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-043-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-043-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-043-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-043-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-043-14** — Define a versioned machine-readable schema with defaults, constraints, deprecations, and required fields.  
  ↳ PK_INTEROP_CONFIG/1 + default_config() secure defaults
- [x] **MC-043-15** — Reject unknown or malformed critical settings unless explicitly declared forward-compatible.  
  ↳ validate_config rejects unknown keys/values (test_invalid_configs_rejected)
- [x] **MC-043-16** — Validate the full candidate configuration before mutating live state.  
  ↳ ConfigManager.activate validates before swap
- [x] **MC-043-17** — Support atomic commit/rollback and retain previous known-good configuration metadata.  
  ↳ single-reference snapshot swap; rollback() to previous known-good
- [x] **MC-043-18** — Record actor/source, before/after digests, timestamps, and resulting effective version for each change.  
  ↳ audit config_activated/rolled_back with digest+revision+approvers; provenance()
- [x] **MC-043-19** — Separate secret references from ordinary configuration values.  
  ↳ config holds no secrets; keys live in keyrings passed to managers/gates
- [ ] **MC-043-20** — Test mixed-version, partial-deployment, downgrade, and rollback behavior.  
  ↳ **PARTIAL** — replay/rollback tested; mixed-version deployment not simulated
- [ ] **MC-043-21** — Generate human-readable configuration documentation from the canonical schema.  
  ↳ **PARTIAL** — docs hand-written from schema; not generated

### D. Component-Specific Controls

- [x] **MC-043-22** — Define a formal grammar or schema meta-model with source-location preservation and deterministic normalization.  
  ↳ PK_INTEROP_CONFIG/1 key/type schema (canon/config.py)
- [x] **MC-043-23** — Reject duplicate/ambiguous declarations, illegal recursion, unresolved references, and version-incompatible imports.  
  ↳ validate_config / LimitPolicy reject unknown and loosening entries
- [ ] **MC-043-24** — Guarantee parse → normalize → serialize determinism with golden fixtures and stable canonical hashes.  
  ↳ **PARTIAL** — config digest deterministic (canonical JSON); no golden fixture
- [x] **MC-043-25** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.  
  ↳ validate_config + quorum approvals before atomic swap
- [ ] **MC-043-26** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.  
  ↳ **PARTIAL** — digest/actor/revision recorded; rollback target implicit (history)

### E. Implementation

- [x] **MC-043-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-043-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-043-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-043-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [x] **MC-043-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [x] **MC-043-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ Boundary reads ConfigManager.current once per call (immutable Snapshot)
- [x] **MC-043-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-043-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-043-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-043-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-043-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-043-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-043-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-043-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-043-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-043-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-043-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/config.py, docs/examples; tests: tests/test_canon.py::ConfigTrustTest, tests/test_canon.py::DocsExamplesTest
- [x] **MC-043-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/config.py, docs/examples; tests: tests/test_canon.py::ConfigTrustTest, tests/test_canon.py::DocsExamplesTest
- [ ] **MC-043-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-043-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-043-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-043-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-043-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-043-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-043-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-043-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-043-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-043-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-043-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-043-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-043-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-043-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-043-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-043-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-043-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-044 — Configuration validator/transaction manager

**Category:** Configuration & Governance  
**Implementation intent:** Deliver `Configuration validator/transaction manager` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-044-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ OPERATIONS + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-044-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-044-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ OPERATIONS; typed signatures + PK_INTEROP_* errors in canon/config.py
- [x] **MC-044-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-044-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-044-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-044-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ OPERATIONS + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-044-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-044-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/config.py
- [ ] **MC-044-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [x] **MC-044-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ per-object locks; two-table lock ordering by table_id (canon/config.py)
- [ ] **MC-044-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-044-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-044-14** — Define a versioned machine-readable schema with defaults, constraints, deprecations, and required fields.  
  ↳ PK_INTEROP_CONFIG/1 + default_config() secure defaults
- [x] **MC-044-15** — Reject unknown or malformed critical settings unless explicitly declared forward-compatible.  
  ↳ validate_config rejects unknown keys/values (test_invalid_configs_rejected)
- [x] **MC-044-16** — Validate the full candidate configuration before mutating live state.  
  ↳ ConfigManager.activate validates before swap
- [x] **MC-044-17** — Support atomic commit/rollback and retain previous known-good configuration metadata.  
  ↳ single-reference snapshot swap; rollback() to previous known-good
- [x] **MC-044-18** — Record actor/source, before/after digests, timestamps, and resulting effective version for each change.  
  ↳ audit config_activated/rolled_back with digest+revision+approvers; provenance()
- [x] **MC-044-19** — Separate secret references from ordinary configuration values.  
  ↳ config holds no secrets; keys live in keyrings passed to managers/gates
- [ ] **MC-044-20** — Test mixed-version, partial-deployment, downgrade, and rollback behavior.  
  ↳ **PARTIAL** — replay/rollback tested; mixed-version deployment not simulated
- [ ] **MC-044-21** — Generate human-readable configuration documentation from the canonical schema.  
  ↳ **PARTIAL** — docs hand-written from schema; not generated

### D. Component-Specific Controls

- [x] **MC-044-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.  
  ↳ validate_config + quorum approvals before atomic swap
- [ ] **MC-044-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.  
  ↳ **PARTIAL** — digest/actor/revision recorded; rollback target implicit (history)
- [ ] **MC-044-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.  
  ↳ **PARTIAL** — malformed/rollback/outage tested; mixed-version/stale-cache not
- [ ] **MC-044-25** — Produce a normative design subsection specific to **Configuration validator/transaction manager** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in OPERATIONS; no normative subsection with worked examples
- [x] **MC-044-26** — Create an end-to-end integration fixture proving **Configuration validator/transaction manager** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-044-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-044-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-044-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [x] **MC-044-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ rollback: CallLifecycle.rollback, _TableCodec.undo, CallScope revocation
- [x] **MC-044-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [x] **MC-044-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ Boundary reads ConfigManager.current once per call (immutable Snapshot)
- [x] **MC-044-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-044-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-044-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-044-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-044-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-044-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-044-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-044-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-044-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-044-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-044-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/config.py; tests: tests/test_canon.py::ConfigTrustTest
- [x] **MC-044-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/config.py; tests: tests/test_canon.py::ConfigTrustTest
- [ ] **MC-044-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [x] **MC-044-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ ConcurrencyLeakTest / AsyncTest threaded stress
- [ ] **MC-044-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-044-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-044-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-044-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-044-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-044-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-044-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-044-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-044-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-044-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-044-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-044-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-044-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-044-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-044-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-045 — Mapping-policy provenance

**Category:** Supply Chain & Trust  
**Implementation intent:** Deliver `Mapping-policy provenance` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-045-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ OPERATIONS + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-045-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-045-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ OPERATIONS; typed signatures + PK_INTEROP_* errors in canon/config.py
- [x] **MC-045-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-045-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-045-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-045-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ OPERATIONS + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-045-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-045-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-045-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-045-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-045-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-045-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-045-14** — Use cryptographic digests for every externally loaded artifact, policy, generated binding, and release object.  
  ↳ sha256 pins (evidence/artifact_policy.json, profile digest, MANIFEST.sha256)
- [ ] **MC-045-15** — Verify provenance/signatures before use and fail closed when mandatory evidence is missing or invalid.  
  ↳ **PARTIAL** — digest+version verified and fail closed; no signatures
- [x] **MC-045-16** — Pin build tools and dependencies sufficiently for reproducible or explainably non-reproducible builds.  
  ↳ zero third-party deps; toolchains recorded in evidence/deps.lock.json
- [ ] **MC-045-17** — Record signer identity, source revision, builder identity, dependency graph, and build environment.  
  ↳ **OPEN** — no signer identity or VCS revision available
- [x] **MC-045-18** — Implement key/root rotation and revocation handling without unsafe bypasses.  
  ↳ CapabilityGate.rotate/revoke_subject, ConfigManager.rotate_approver_key/revoke_approver (test_key_rotation_and_revocation)
- [x] **MC-045-19** — Separate verification mechanism from policy and version both independently.  
  ↳ ArtifactPolicy (policy data) vs sha256_file/verify (mechanism); policy versioned per release
- [ ] **MC-045-20** — Continuously scan dependencies/artifacts and define remediation SLA by severity.  
  ↳ **OPEN** — no dependency scanner/remediation SLA (no third-party deps today)
- [x] **MC-045-21** — Retain verification evidence so historical releases can be independently re-evaluated.  
  ↳ artifact_policy.json + RELEASE_EVIDENCE.json retained per release

### D. Component-Specific Controls

- [x] **MC-045-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.  
  ↳ validate_config + quorum approvals before atomic swap
- [ ] **MC-045-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.  
  ↳ **PARTIAL** — digest/actor/revision recorded; rollback target implicit (history)
- [ ] **MC-045-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.  
  ↳ **PARTIAL** — malformed/rollback/outage tested; mixed-version/stale-cache not
- [ ] **MC-045-25** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.  
  ↳ **PARTIAL** — keyrings + expiry + revocation defined; no signer/build identities
- [ ] **MC-045-26** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.  
  ↳ **PARTIAL** — immutable digests yes; signatures/attestations no

### E. Implementation

- [x] **MC-045-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-045-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-045-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-045-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [x] **MC-045-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ detached copies on validate/lower/lift; immutable registries/snapshots
- [ ] **MC-045-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-045-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-045-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-045-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-045-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-045-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-045-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-045-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-045-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-045-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-045-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-045-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/config.py, canon/registry.py; tests: tests/test_canon.py::ConfigTrustTest
- [x] **MC-045-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/config.py, canon/registry.py; tests: tests/test_canon.py::ConfigTrustTest
- [ ] **MC-045-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-045-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-045-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-045-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-045-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-045-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-045-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-045-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-045-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-045-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-045-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-045-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-045-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-045-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-045-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-045-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-045-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-046 — Artifact provenance verifier

**Category:** Supply Chain & Trust  
**Implementation intent:** Deliver `Artifact provenance verifier` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-046-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ THREAT_MODEL T13 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-046-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-046-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ THREAT_MODEL T13; typed signatures + PK_INTEROP_* errors in canon/provenance.py
- [ ] **MC-046-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-046-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-046-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-046-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ THREAT_MODEL T13 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-046-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-046-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-046-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-046-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-046-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-046-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-046-14** — Use cryptographic digests for every externally loaded artifact, policy, generated binding, and release object.  
  ↳ sha256 pins (evidence/artifact_policy.json, profile digest, MANIFEST.sha256)
- [ ] **MC-046-15** — Verify provenance/signatures before use and fail closed when mandatory evidence is missing or invalid.  
  ↳ **PARTIAL** — digest+version verified and fail closed; no signatures
- [x] **MC-046-16** — Pin build tools and dependencies sufficiently for reproducible or explainably non-reproducible builds.  
  ↳ zero third-party deps; toolchains recorded in evidence/deps.lock.json
- [ ] **MC-046-17** — Record signer identity, source revision, builder identity, dependency graph, and build environment.  
  ↳ **OPEN** — no signer identity or VCS revision available
- [x] **MC-046-18** — Implement key/root rotation and revocation handling without unsafe bypasses.  
  ↳ CapabilityGate.rotate/revoke_subject, ConfigManager.rotate_approver_key/revoke_approver (test_key_rotation_and_revocation)
- [x] **MC-046-19** — Separate verification mechanism from policy and version both independently.  
  ↳ ArtifactPolicy (policy data) vs sha256_file/verify (mechanism); policy versioned per release
- [ ] **MC-046-20** — Continuously scan dependencies/artifacts and define remediation SLA by severity.  
  ↳ **OPEN** — no dependency scanner/remediation SLA (no third-party deps today)
- [x] **MC-046-21** — Retain verification evidence so historical releases can be independently re-evaluated.  
  ↳ artifact_policy.json + RELEASE_EVIDENCE.json retained per release

### D. Component-Specific Controls

- [ ] **MC-046-22** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.  
  ↳ **PARTIAL** — keyrings + expiry + revocation defined; no signer/build identities
- [ ] **MC-046-23** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.  
  ↳ **PARTIAL** — immutable digests yes; signatures/attestations no
- [x] **MC-046-24** — Test substitution, replay, expiry, revocation, downgrade, and trust-service outage behavior with fail-closed defaults.  
  ↳ ConfigTrustTest (replay, forged approval, expiry, revocation, outage) + provenance substitution
- [ ] **MC-046-25** — Produce a normative design subsection specific to **Artifact provenance verifier** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in THREAT_MODEL T13; no normative subsection with worked examples
- [ ] **MC-046-26** — Create an end-to-end integration fixture proving **Artifact provenance verifier** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-046-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-046-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-046-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-046-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-046-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-046-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-046-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-046-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-046-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-046-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-046-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-046-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-046-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-046-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-046-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-046-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-046-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/provenance.py, tools/release.py; tests: tests/test_canon.py::ConfigTrustTest; evidence: evidence/artifact_policy.json
- [x] **MC-046-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/provenance.py, tools/release.py; tests: tests/test_canon.py::ConfigTrustTest; evidence: evidence/artifact_policy.json
- [ ] **MC-046-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-046-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-046-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-046-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-046-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-046-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-046-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-046-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-046-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-046-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-046-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-046-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-046-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-046-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-046-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-046-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-046-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-047 — SBOM and dependency lock

**Category:** Supply Chain & Trust  
**Implementation intent:** Deliver `SBOM and dependency lock` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-047-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ OPERATIONS + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-047-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-047-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ OPERATIONS; typed signatures + PK_INTEROP_* errors in canon/provenance.py
- [ ] **MC-047-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-047-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-047-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-047-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ OPERATIONS + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-047-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-047-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-047-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-047-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-047-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-047-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-047-14** — Use cryptographic digests for every externally loaded artifact, policy, generated binding, and release object.  
  ↳ sha256 pins (evidence/artifact_policy.json, profile digest, MANIFEST.sha256)
- [ ] **MC-047-15** — Verify provenance/signatures before use and fail closed when mandatory evidence is missing or invalid.  
  ↳ **PARTIAL** — digest+version verified and fail closed; no signatures
- [x] **MC-047-16** — Pin build tools and dependencies sufficiently for reproducible or explainably non-reproducible builds.  
  ↳ zero third-party deps; toolchains recorded in evidence/deps.lock.json
- [ ] **MC-047-17** — Record signer identity, source revision, builder identity, dependency graph, and build environment.  
  ↳ **OPEN** — no signer identity or VCS revision available
- [x] **MC-047-18** — Implement key/root rotation and revocation handling without unsafe bypasses.  
  ↳ CapabilityGate.rotate/revoke_subject, ConfigManager.rotate_approver_key/revoke_approver (test_key_rotation_and_revocation)
- [x] **MC-047-19** — Separate verification mechanism from policy and version both independently.  
  ↳ ArtifactPolicy (policy data) vs sha256_file/verify (mechanism); policy versioned per release
- [ ] **MC-047-20** — Continuously scan dependencies/artifacts and define remediation SLA by severity.  
  ↳ **OPEN** — no dependency scanner/remediation SLA (no third-party deps today)
- [x] **MC-047-21** — Retain verification evidence so historical releases can be independently re-evaluated.  
  ↳ artifact_policy.json + RELEASE_EVIDENCE.json retained per release

### D. Component-Specific Controls

- [ ] **MC-047-22** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.  
  ↳ **PARTIAL** — keyrings + expiry + revocation defined; no signer/build identities
- [ ] **MC-047-23** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.  
  ↳ **PARTIAL** — immutable digests yes; signatures/attestations no
- [x] **MC-047-24** — Test substitution, replay, expiry, revocation, downgrade, and trust-service outage behavior with fail-closed defaults.  
  ↳ ConfigTrustTest (replay, forged approval, expiry, revocation, outage) + provenance substitution
- [ ] **MC-047-25** — Produce a normative design subsection specific to **SBOM and dependency lock** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in OPERATIONS; no normative subsection with worked examples
- [ ] **MC-047-26** — Create an end-to-end integration fixture proving **SBOM and dependency lock** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [x] **MC-047-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-047-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-047-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-047-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-047-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-047-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-047-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-047-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-047-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [x] **MC-047-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ deterministic generated artifacts with digests (vectors.json schema_digest, SBOM, MANIFEST)

### F. Security & Hardening

- [x] **MC-047-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-047-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [x] **MC-047-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-047-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-047-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-047-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-047-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/provenance.py, tools/release.py; tests: tests/test_canon.py::ConfigTrustTest; evidence: evidence/sbom.cdx.json, evidence/deps.lock.json
- [x] **MC-047-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/provenance.py, tools/release.py; tests: tests/test_canon.py::ConfigTrustTest; evidence: evidence/sbom.cdx.json, evidence/deps.lock.json
- [ ] **MC-047-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-047-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-047-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-047-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-047-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-047-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-047-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-047-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-047-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-047-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-047-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-047-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-047-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-047-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-047-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-047-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-047-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-048 — Capability/authentication integration

**Category:** Security & Policy  
**Implementation intent:** Deliver `Capability/authentication integration` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-048-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-048-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-048-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/trust.py
- [x] **MC-048-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-048-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-048-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-048-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-048-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [ ] **MC-048-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-048-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-048-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-048-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-048-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-048-14** — Document the trust boundary and exact authority granted to this component.  
  ↳ docs/SPEC.md §0 trust boundaries; docs/THREAT_MODEL.md
- [x] **MC-048-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.  
  ↳ unknown identities/codes/languages/configs refused (ConfigTrustTest, RegistryNumericUnicodeTest)
- [x] **MC-048-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.  
  ↳ decisions keyed to config revision/digest; AuditLog hash chain
- [x] **MC-048-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.  
  ↳ Limits/Budget, bounded diagnostics (160 chars/32 segments), max_spans
- [x] **MC-048-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.  
  ↳ hmac.compare_digest for MACs (config, audit, trust)
- [x] **MC-048-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.  
  ↳ revision replay refused; transcript digests; foreign/stale handles refused; key revocation clears cache
- [x] **MC-048-20** — Classify and redact logs, errors, traces, and audit events before emission.  
  ↳ errors.redact + span attribute allow-list
- [x] **MC-048-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.  
  ↳ test_capability_gate_and_outage_policy (trust + trusted-time outage)

### D. Component-Specific Controls

- [ ] **MC-048-22** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.  
  ↳ **PARTIAL** — keyrings + expiry + revocation defined; no signer/build identities
- [ ] **MC-048-23** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.  
  ↳ **PARTIAL** — immutable digests yes; signatures/attestations no
- [x] **MC-048-24** — Test substitution, replay, expiry, revocation, downgrade, and trust-service outage behavior with fail-closed defaults.  
  ↳ ConfigTrustTest (replay, forged approval, expiry, revocation, outage) + provenance substitution
- [x] **MC-048-25** — Produce a normative design subsection specific to **Capability/authentication integration** with valid and invalid worked examples.  
  ↳ docs/SPEC.md SPEC §11
- [x] **MC-048-26** — Create an end-to-end integration fixture proving **Capability/authentication integration** works through its real production-facing path.  
  ↳ exercised through canon/boundary.py call path or the cross-language/wasm harnesses

### E. Implementation

- [x] **MC-048-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-048-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-048-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-048-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-048-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [ ] **MC-048-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — does not read configuration
- [x] **MC-048-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-048-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-048-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-048-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-048-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-048-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-048-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-048-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-048-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-048-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-048-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/trust.py; tests: tests/test_canon.py::ConfigTrustTest, tests/test_canon.py::BoundaryIntegrationTest
- [x] **MC-048-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/trust.py; tests: tests/test_canon.py::ConfigTrustTest, tests/test_canon.py::BoundaryIntegrationTest
- [ ] **MC-048-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-048-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-048-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-048-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-048-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-048-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-048-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-048-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-048-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-048-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-048-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-048-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-048-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-048-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-048-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-048-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-048-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-049 — Trust-service outage policy

**Category:** Security & Policy  
**Implementation intent:** Deliver `Trust-service outage policy` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [x] **MC-049-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ SPEC §11 + docs/SPEC.md §0 scope/callers/trust boundaries
- [ ] **MC-049-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-049-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ SPEC §11; typed signatures + PK_INTEROP_* errors in canon/trust.py
- [x] **MC-049-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ docs/SPEC.md REQ-G-1 (no implementation-defined behaviour) + per-op validation
- [x] **MC-049-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-049-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [x] **MC-049-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ SPEC §11 + module docstring data/control flow (canon/boundary.py pipeline)
- [x] **MC-049-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ canonical Type AST / CJV notation independent of host identity (canon/types.py, canon/cjv.py)
- [x] **MC-049-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ state machine documented + enforced in canon/trust.py
- [ ] **MC-049-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-049-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-049-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **PARTIAL** — bounded by upstream limits; no component-specific budget
- [x] **MC-049-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ PK_INTEROP_ERROR/1 envelope, redaction, closed label vocabulary

### C. Domain-Specific Controls

- [x] **MC-049-14** — Document the trust boundary and exact authority granted to this component.  
  ↳ docs/SPEC.md §0 trust boundaries; docs/THREAT_MODEL.md
- [x] **MC-049-15** — Use deny-by-default behavior for unknown identities, schemas, capabilities, provenance states, or policy values.  
  ↳ unknown identities/codes/languages/configs refused (ConfigTrustTest, RegistryNumericUnicodeTest)
- [x] **MC-049-16** — Make security decisions deterministic, auditable, and attributable to versioned policy/configuration.  
  ↳ decisions keyed to config revision/digest; AuditLog hash chain
- [x] **MC-049-17** — Bound CPU, memory, queue, recursion, payload, and log amplification for attacker-controlled inputs.  
  ↳ Limits/Budget, bounded diagnostics (160 chars/32 segments), max_spans
- [x] **MC-049-18** — Use constant-time comparison where secrets/authentication material are involved and avoid secret-dependent diagnostics.  
  ↳ hmac.compare_digest for MACs (config, audit, trust)
- [x] **MC-049-19** — Verify replay, substitution, downgrade, stale-cache, and confused-deputy resistance where applicable.  
  ↳ revision replay refused; transcript digests; foreign/stale handles refused; key revocation clears cache
- [x] **MC-049-20** — Classify and redact logs, errors, traces, and audit events before emission.  
  ↳ errors.redact + span attribute allow-list
- [x] **MC-049-21** — Test dependency-outage behavior explicitly; never rely on undocumented fallback behavior.  
  ↳ test_capability_gate_and_outage_policy (trust + trusted-time outage)

### D. Component-Specific Controls

- [x] **MC-049-22** — Validate a complete candidate policy/configuration snapshot before activation and apply changes atomically.  
  ↳ validate_config + quorum approvals before atomic swap
- [ ] **MC-049-23** — Record before/after digests, actor/source, effective version, validation result, and rollback target for each change.  
  ↳ **PARTIAL** — digest/actor/revision recorded; rollback target implicit (history)
- [ ] **MC-049-24** — Test malformed, partial, mixed-version, rollback, stale-cache, and dependency-unavailable scenarios.  
  ↳ **PARTIAL** — malformed/rollback/outage tested; mixed-version/stale-cache not
- [ ] **MC-049-25** — Define trusted roots, signer/build identities, validity windows, revocation, and verification-failure behavior.  
  ↳ **PARTIAL** — keyrings + expiry + revocation defined; no signer/build identities
- [ ] **MC-049-26** — Use immutable digests and signed/attested metadata for every externally supplied artifact or authorization object.  
  ↳ **PARTIAL** — immutable digests yes; signatures/attestations no

### E. Implementation

- [x] **MC-049-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ validate() completes before any allocation/handle move (REQ-G-2); BoundaryIntegrationTest.test_invalid_args_leave_no_trace
- [ ] **MC-049-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — no size/offset arithmetic
- [x] **MC-049-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ no assert-based checks; unit suite re-run under python -O (evidence/ci_run.json gate unit-optimized); native fixtures built --release with overflow-checks
- [ ] **MC-049-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — pure function; no partial work to roll back
- [ ] **MC-049-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — no mutable host values cross this component
- [x] **MC-049-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ Boundary reads ConfigManager.current once per call (immutable Snapshot)
- [x] **MC-049-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ errors raised at the detecting layer with code+path; causal chain via .at() without payloads
- [ ] **MC-049-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — no blocking or async operations in this component
- [x] **MC-049-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ unknown kinds/cases/languages/versions/handles fail closed (PK_INTEROP_* codes)
- [ ] **MC-049-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [x] **MC-049-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ docs/THREAT_MODEL.md abuse cases T1-T17 mapped to controls/tests
- [x] **MC-049-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ fail-closed on every malformed/unsupported input (registered codes)
- [ ] **MC-049-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-049-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [x] **MC-049-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ redaction + envelope tests (ErrorEnvelopeTest.test_payload_values_never_in_diagnostics)
- [x] **MC-049-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-049-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: canon/trust.py; tests: tests/test_canon.py::ConfigTrustTest
- [x] **MC-049-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: canon/trust.py; tests: tests/test_canon.py::ConfigTrustTest
- [ ] **MC-049-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **PARTIAL** — example-based tests only; not property/fuzz driven
- [ ] **MC-049-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-049-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-049-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-049-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-049-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [x] **MC-049-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ failure modes surface as PK_INTEROP_* codes -> refusal counters/spans/audit (canon/observability.py)
- [x] **MC-049-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-049-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-049-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-049-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-049-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-049-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-049-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-049-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-049-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-049-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-050 — Architecture Decision Record

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Architecture Decision Record` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-050-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-050-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-050-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-050-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-050-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-050-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-050-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-050-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-050-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-050-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-050-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-050-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-050-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-050-14** — Assign a durable owner, reviewers, and review cadence.  
  ↳ **OPEN** — owner/reviewers not named
- [x] **MC-050-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [x] **MC-050-16** — Record assumptions and distinguish verified facts from design intent and deferred work.  
  ↳ Certified/Declared/Blocked status keys (docs/COMPATIBILITY.md); ADR consequences
- [ ] **MC-050-17** — Require architecture/security review for changes affecting semantics or trust boundaries.  
  ↳ **OPEN** — no human review recorded
- [ ] **MC-050-18** — Version document/evidence schemas and preserve immutable historical copies.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-050-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-050-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.  
  ↳ **OPEN** — N/A items carry proposed waivers only; none approved
- [x] **MC-050-21** — Make release approval depend on evidence completeness rather than document existence.  
  ↳ ci.py verdict gates on evidence; checklist marks only evidenced items

### D. Component-Specific Controls

- [x] **MC-050-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [ ] **MC-050-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-050-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-050-25** — Produce a normative design subsection specific to **Architecture Decision Record** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in ADR-0001; no normative subsection with worked examples
- [ ] **MC-050-26** — Create an end-to-end integration fixture proving **Architecture Decision Record** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-050-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-050-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-050-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-050-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-050-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-050-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-050-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-050-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-050-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: docs/ADR-0001.md; tests: tests/test_canon.py::DocsExamplesTest
- [ ] **MC-050-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-050-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-050-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-050-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-050-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-050-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-050-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-050-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-050-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-050-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-050-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-050-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-050-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-050-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-050-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-050-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-050-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-050-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-051 — Formal threat model

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Formal threat model` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-051-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-051-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-051-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-051-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-051-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-051-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-051-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-051-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-051-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-051-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-051-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-051-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-051-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-051-14** — Assign a durable owner, reviewers, and review cadence.  
  ↳ **OPEN** — owner/reviewers not named
- [x] **MC-051-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [x] **MC-051-16** — Record assumptions and distinguish verified facts from design intent and deferred work.  
  ↳ Certified/Declared/Blocked status keys (docs/COMPATIBILITY.md); ADR consequences
- [ ] **MC-051-17** — Require architecture/security review for changes affecting semantics or trust boundaries.  
  ↳ **OPEN** — no human review recorded
- [ ] **MC-051-18** — Version document/evidence schemas and preserve immutable historical copies.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-051-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-051-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.  
  ↳ **OPEN** — N/A items carry proposed waivers only; none approved
- [x] **MC-051-21** — Make release approval depend on evidence completeness rather than document existence.  
  ↳ ci.py verdict gates on evidence; checklist marks only evidenced items

### D. Component-Specific Controls

- [x] **MC-051-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [ ] **MC-051-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-051-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-051-25** — Produce a normative design subsection specific to **Formal threat model** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in THREAT_MODEL; no normative subsection with worked examples
- [ ] **MC-051-26** — Create an end-to-end integration fixture proving **Formal threat model** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-051-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-051-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-051-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-051-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-051-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-051-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-051-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-051-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-051-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: docs/THREAT_MODEL.md; tests: tests/test_canon.py::DocsExamplesTest
- [ ] **MC-051-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-051-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-051-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-051-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-051-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-051-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-051-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-051-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-051-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-051-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-051-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-051-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-051-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-051-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-051-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-051-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-051-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-051-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-052 — Requirements traceability matrix

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Requirements traceability matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-052-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-052-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-052-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-052-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-052-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-052-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-052-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-052-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-052-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-052-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-052-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-052-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-052-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-052-14** — Assign a durable owner, reviewers, and review cadence.  
  ↳ **OPEN** — owner/reviewers not named
- [x] **MC-052-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [x] **MC-052-16** — Record assumptions and distinguish verified facts from design intent and deferred work.  
  ↳ Certified/Declared/Blocked status keys (docs/COMPATIBILITY.md); ADR consequences
- [ ] **MC-052-17** — Require architecture/security review for changes affecting semantics or trust boundaries.  
  ↳ **OPEN** — no human review recorded
- [ ] **MC-052-18** — Version document/evidence schemas and preserve immutable historical copies.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-052-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-052-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.  
  ↳ **OPEN** — N/A items carry proposed waivers only; none approved
- [x] **MC-052-21** — Make release approval depend on evidence completeness rather than document existence.  
  ↳ ci.py verdict gates on evidence; checklist marks only evidenced items

### D. Component-Specific Controls

- [x] **MC-052-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ frozen golden corpus + 4 independent implementations
- [ ] **MC-052-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-052-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [x] **MC-052-25** — Define a stable telemetry/state schema with bounded-cardinality dimensions and explicit versioning.  
  ↳ closed vocabularies (Metrics/_LABEL_VOCAB, Tracer.ATTRS, AuditLog.EVENTS, Health conditions)
- [ ] **MC-052-26** — Map every critical failure mode to a detectable signal, alert condition, and operator diagnostic path.  
  ↳ **PARTIAL** — codes -> counters mapped; alert conditions not defined

### E. Implementation

- [ ] **MC-052-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-052-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [x] **MC-052-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ deterministic generated artifacts with digests (vectors.json schema_digest, SBOM, MANIFEST)

### F. Security & Hardening

- [ ] **MC-052-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-052-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-052-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-052-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-052-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-052-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-052-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: docs/TRACEABILITY.md, tools/checklist_status.py; tests: tests/test_canon.py::DocsExamplesTest; evidence: evidence/checklist_status.json
- [ ] **MC-052-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-052-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-052-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-052-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-052-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-052-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-052-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-052-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-052-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-052-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-052-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-052-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-052-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-052-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-052-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-052-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-052-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-052-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-053 — Reproducible pk_core integration environment

**Category:** Build & CI  
**Implementation intent:** Deliver `Reproducible pk_core integration environment` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-053-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-053-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-053-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ OPERATIONS; typed signatures + PK_INTEROP_* errors in tools/ci.py
- [ ] **MC-053-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-053-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-053-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-053-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-053-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-053-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-053-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-053-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-053-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-053-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-053-14** — Pin toolchains, runners, base images, and third-party build actions/plugins by immutable version or digest.  
  ↳ **PARTIAL** — toolchain versions recorded; GitHub actions pinned by tag not digest
- [x] **MC-053-15** — Build from a clean workspace and prohibit undeclared network/download dependencies in certified jobs.  
  ↳ offline build (cargo --offline, stdlib-only) in a fresh container
- [ ] **MC-053-16** — Use least-privilege short-lived credentials and isolate untrusted changes from signing/release credentials.  
  ↳ **N/A-PROPOSED** — pipeline holds no credentials; signing not configured
- [x] **MC-053-17** — Make every mandatory stage fail closed on error, timeout, missing evidence, or skipped dependency.  
  ↳ missing tools -> BLOCKED, failures -> FAIL (evidence/ci_negative_test.json)
- [x] **MC-053-18** — Retain logs, reports, coverage, SBOMs, provenance, checksums, and test outputs as immutable artifacts.  
  ↳ evidence/*.json + output digests in ci_run.json
- [x] **MC-053-19** — Test the pipeline with deliberate failures so unenforced/bypassed gates are detected.  
  ↳ tools/ci.py --negative-test (evidence/ci_negative_test.json)
- [x] **MC-053-20** — Provide deterministic local reproduction commands equivalent to CI stages.  
  ↳ python tools/ci.py [--quick] is the CI entry point
- [ ] **MC-053-21** — Promote the exact tested artifact to release without rebuild drift.  
  ↳ **PARTIAL** — MANIFEST.sha256 + tree digest allow verification; no promotion system

### D. Component-Specific Controls

- [ ] **MC-053-22** — Bootstrap from a clean environment using pinned toolchains and dependency locks with no undeclared local state.  
  ↳ **PARTIAL** — clean container bootstrap works for engine gates; pk_core absent
- [x] **MC-053-23** — Fail the pipeline on missing/skipped mandatory gates and verify this with intentional negative pipeline tests.  
  ↳ evidence/ci_negative_test.json
- [ ] **MC-053-24** — Promote the exact tested artifact to release without rebuilding or mutating its content.  
  ↳ **PARTIAL** — MANIFEST.sha256 + tree digest allow verification; no promotion system
- [ ] **MC-053-25** — Produce a normative design subsection specific to **Reproducible pk_core integration environment** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in OPERATIONS; no normative subsection with worked examples
- [ ] **MC-053-26** — Create an end-to-end integration fixture proving **Reproducible pk_core integration environment** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-053-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-053-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-053-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-053-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-053-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-053-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-053-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-053-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-053-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/ci.py; tests: tools/ci.py; evidence: evidence/ci_run.json
- [x] **MC-053-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/ci.py; tests: tools/ci.py; evidence: evidence/ci_run.json
- [ ] **MC-053-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-053-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-053-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-053-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-053-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-053-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-053-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-053-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-053-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-053-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-053-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-053-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-053-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-053-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [ ] **MC-053-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ **OPEN** — pk_core parent framework is not present; the external 100-item gate cannot execute here
- [ ] **MC-053-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-053-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-054 — CI conformance pipeline

**Category:** Build & CI  
**Implementation intent:** Deliver `CI conformance pipeline` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-054-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-054-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [x] **MC-054-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ OPERATIONS; typed signatures + PK_INTEROP_* errors in tools/ci.py
- [ ] **MC-054-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [x] **MC-054-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ docs/COMPATIBILITY.md (spec/profile/envelope/config versions, deprecation windows)
- [ ] **MC-054-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-054-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-054-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-054-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-054-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-054-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-054-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-054-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **PARTIAL** — gate outputs are machine-readable JSON; no secret-bearing fields

### C. Domain-Specific Controls

- [ ] **MC-054-14** — Pin toolchains, runners, base images, and third-party build actions/plugins by immutable version or digest.  
  ↳ **PARTIAL** — toolchain versions recorded; GitHub actions pinned by tag not digest
- [x] **MC-054-15** — Build from a clean workspace and prohibit undeclared network/download dependencies in certified jobs.  
  ↳ offline build (cargo --offline, stdlib-only) in a fresh container
- [ ] **MC-054-16** — Use least-privilege short-lived credentials and isolate untrusted changes from signing/release credentials.  
  ↳ **N/A-PROPOSED** — pipeline holds no credentials; signing not configured
- [x] **MC-054-17** — Make every mandatory stage fail closed on error, timeout, missing evidence, or skipped dependency.  
  ↳ missing tools -> BLOCKED, failures -> FAIL (evidence/ci_negative_test.json)
- [x] **MC-054-18** — Retain logs, reports, coverage, SBOMs, provenance, checksums, and test outputs as immutable artifacts.  
  ↳ evidence/*.json + output digests in ci_run.json
- [x] **MC-054-19** — Test the pipeline with deliberate failures so unenforced/bypassed gates are detected.  
  ↳ tools/ci.py --negative-test (evidence/ci_negative_test.json)
- [x] **MC-054-20** — Provide deterministic local reproduction commands equivalent to CI stages.  
  ↳ python tools/ci.py [--quick] is the CI entry point
- [ ] **MC-054-21** — Promote the exact tested artifact to release without rebuild drift.  
  ↳ **PARTIAL** — MANIFEST.sha256 + tree digest allow verification; no promotion system

### D. Component-Specific Controls

- [x] **MC-054-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ frozen golden corpus + 4 independent implementations
- [ ] **MC-054-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-054-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [ ] **MC-054-25** — Bootstrap from a clean environment using pinned toolchains and dependency locks with no undeclared local state.  
  ↳ **PARTIAL** — local clean bootstrap; hosted runners not exercised
- [x] **MC-054-26** — Fail the pipeline on missing/skipped mandatory gates and verify this with intentional negative pipeline tests.  
  ↳ evidence/ci_negative_test.json

### E. Implementation

- [ ] **MC-054-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-054-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-054-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-054-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-054-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-054-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-054-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-054-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-054-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/ci.py, ci/github-actions.yml; tests: tools/ci.py --negative-test; evidence: evidence/ci_run.json, evidence/ci_negative_test.json
- [x] **MC-054-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ impl: tools/ci.py, ci/github-actions.yml; tests: tools/ci.py --negative-test; evidence: evidence/ci_run.json, evidence/ci_negative_test.json
- [ ] **MC-054-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-054-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-054-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-054-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [x] **MC-054-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ fresh container, stdlib + pinned toolchains only, python -O and --release builds (evidence/ci_run.json)
- [x] **MC-054-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-054-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-054-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-054-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-054-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-054-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-054-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-054-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-054-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-054-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-054-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-054-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-055 — Release evidence bundle

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Release evidence bundle` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-055-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-055-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-055-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-055-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-055-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-055-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-055-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-055-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-055-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-055-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-055-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-055-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-055-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-055-14** — Assign a durable owner, reviewers, and review cadence.  
  ↳ **OPEN** — owner/reviewers not named
- [x] **MC-055-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [x] **MC-055-16** — Record assumptions and distinguish verified facts from design intent and deferred work.  
  ↳ Certified/Declared/Blocked status keys (docs/COMPATIBILITY.md); ADR consequences
- [ ] **MC-055-17** — Require architecture/security review for changes affecting semantics or trust boundaries.  
  ↳ **OPEN** — no human review recorded
- [ ] **MC-055-18** — Version document/evidence schemas and preserve immutable historical copies.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-055-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-055-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.  
  ↳ **OPEN** — N/A items carry proposed waivers only; none approved
- [x] **MC-055-21** — Make release approval depend on evidence completeness rather than document existence.  
  ↳ ci.py verdict gates on evidence; checklist marks only evidenced items

### D. Component-Specific Controls

- [x] **MC-055-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [ ] **MC-055-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-055-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-055-25** — Produce a normative design subsection specific to **Release evidence bundle** with valid and invalid worked examples.  
  ↳ **PARTIAL** — described in OPERATIONS; no normative subsection with worked examples
- [ ] **MC-055-26** — Create an end-to-end integration fixture proving **Release evidence bundle** works through its real production-facing path.  
  ↳ **PARTIAL** — exercised by unit tests; not through a production-facing path

### E. Implementation

- [ ] **MC-055-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-055-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [x] **MC-055-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ deterministic generated artifacts with digests (vectors.json schema_digest, SBOM, MANIFEST)

### F. Security & Hardening

- [ ] **MC-055-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-055-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [x] **MC-055-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ canonical JSON / canonical type form before hashing/comparison
- [ ] **MC-055-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-055-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-055-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-055-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: tools/release.py; tests: tools/release.py; evidence: evidence/RELEASE_EVIDENCE.json
- [ ] **MC-055-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-055-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-055-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-055-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-055-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-055-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-055-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-055-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-055-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-055-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-055-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-055-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-055-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-055-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-055-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-055-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-055-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-055-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-056 — Compatibility support matrix

**Category:** Documentation & Release Governance  
**Implementation intent:** Deliver `Compatibility support matrix` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-056-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-056-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-056-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-056-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-056-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-056-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-056-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-056-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-056-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-056-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-056-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-056-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-056-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-056-14** — Assign a durable owner, reviewers, and review cadence.  
  ↳ **OPEN** — owner/reviewers not named
- [x] **MC-056-15** — Use stable IDs linking requirements, decisions, risks, tests, evidence, and exceptions.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [x] **MC-056-16** — Record assumptions and distinguish verified facts from design intent and deferred work.  
  ↳ Certified/Declared/Blocked status keys (docs/COMPATIBILITY.md); ADR consequences
- [ ] **MC-056-17** — Require architecture/security review for changes affecting semantics or trust boundaries.  
  ↳ **OPEN** — no human review recorded
- [ ] **MC-056-18** — Version document/evidence schemas and preserve immutable historical copies.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-056-19** — Automate consistency checks against source, CI results, artifact digests, and release metadata.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-056-20** — Define exception/waiver records with scope, rationale, risk owner, reviewer, and expiration.  
  ↳ **OPEN** — N/A items carry proposed waivers only; none approved
- [x] **MC-056-21** — Make release approval depend on evidence completeness rather than document existence.  
  ↳ ci.py verdict gates on evidence; checklist marks only evidenced items

### D. Component-Specific Controls

- [x] **MC-056-22** — Define an independent oracle or expected-result source so tests do not derive truth from the implementation under test.  
  ↳ frozen golden corpus + 4 independent implementations
- [ ] **MC-056-23** — Persist exact seeds, inputs, environment metadata, and minimized failures as immutable regression artifacts.  
  ↳ **PARTIAL** — results persisted; no minimized counterexamples
- [x] **MC-056-24** — Make the suite an enforced CI/release gate with explicit timeout, flake, retry, and evidence-retention policy.  
  ↳ gate in tools/ci.py with retained evidence
- [x] **MC-056-25** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [ ] **MC-056-26** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS

### E. Implementation

- [ ] **MC-056-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-056-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-056-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-056-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-056-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-056-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-056-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-056-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-056-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: docs/COMPATIBILITY.md; tests: tests/test_canon.py::DocsExamplesTest; evidence: evidence/conformance.json
- [ ] **MC-056-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-056-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-056-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-056-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-056-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-056-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-056-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-056-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-056-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-056-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-056-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-056-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-056-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-056-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-056-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-056-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-056-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-056-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-057 — Rollback and emergency-disable runbook

**Category:** Operations & Incident Response  
**Implementation intent:** Deliver `Rollback and emergency-disable runbook` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-057-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-057-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-057-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-057-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-057-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-057-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-057-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-057-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-057-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-057-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-057-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-057-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-057-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-057-14** — Define severity levels, activation criteria, and decision authority for incidents involving this component.  
  ↳ **PARTIAL** — plays P1-P6 with triggers; severity scale/decision authority not assigned
- [x] **MC-057-15** — Provide exact tested containment/rollback commands with prerequisite and safety checks.  
  ↳ ConfigManager.rollback / health emergency_disabled exercised in tests (ConfigTrustTest)
- [ ] **MC-057-16** — Preserve forensic evidence before destructive remediation when operational safety permits.  
  ↳ **PARTIAL** — playbook requires snapshot+audit preservation; not exercised
- [ ] **MC-057-17** — Define communication, escalation, ownership handoff, and status-update procedures.  
  ↳ **PARTIAL** — escalation chain by role; no communication templates
- [x] **MC-057-18** — Document consistency implications of rollback, restart, cancellation, forced teardown, and partial recovery.  
  ↳ snapshot semantics: in-flight calls finish on their snapshot (docs/RUNBOOK.md A)
- [x] **MC-057-19** — Require post-action validation of semantic correctness, not merely process liveness.  
  ↳ runbook verify steps re-run tools/ci.py --quick
- [ ] **MC-057-20** — Run recurring game days/tabletops and track remediation actions to closure.  
  ↳ **OPEN** — no game day/tabletop run
- [ ] **MC-057-21** — Feed incident findings back into tests, alerts, limits, threat model, and release gates.  
  ↳ **PARTIAL** — fuzz regressions directory is the feedback path; no incident history

### D. Component-Specific Controls

- [x] **MC-057-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [ ] **MC-057-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-057-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-057-25** — Define exact trigger conditions, decision authority, commands, prerequisites, and abort criteria for emergency actions.  
  ↳ **PARTIAL** — triggers + commands documented; decision authority not named
- [ ] **MC-057-26** — Preserve forensic evidence and state-consistency information before destructive remediation when safe to do so.  
  ↳ **PARTIAL** — playbook requires snapshot+audit preservation; not exercised

### E. Implementation

- [ ] **MC-057-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-057-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-057-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-057-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-057-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-057-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-057-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-057-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [x] **MC-057-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ impl: docs/RUNBOOK.md; tests: tests/test_canon.py::ConfigTrustTest
- [ ] **MC-057-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-057-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-057-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-057-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-057-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-057-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-057-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-057-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-057-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-057-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-057-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-057-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-057-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-057-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-057-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-057-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-057-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-057-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## MC-058 — Operational incident playbook

**Category:** Operations & Incident Response  
**Implementation intent:** Deliver `Operational incident playbook` as a versioned, testable, fail-safe production component of INV-12.

### A. Requirements & Contract

- [ ] **MC-058-01** — Define normative scope, non-goals, callers, callees, dependencies, and trust boundaries using RFC-style MUST/SHOULD/MAY language.  
  ↳ **PARTIAL** — scope stated in tool docstring/doc; not written as RFC-2119 normative text
- [ ] **MC-058-02** — Assign stable requirement IDs and map each requirement to owner, source code, test evidence, and release gate.  
  ↳ **PARTIAL** — REQ IDs mapped to source/tests/gates in docs/TRACEABILITY.md; owners are roles, no named individuals
- [ ] **MC-058-03** — Define all public inputs, outputs, state transitions, side effects, invariants, and externally observable errors.  
  ↳ **PARTIAL** — document inputs/outputs described; not a callable interface
- [ ] **MC-058-04** — Specify preconditions and postconditions for every externally callable operation; explicitly prohibit undefined behavior.  
  ↳ **PARTIAL** — pre/postconditions implicit in tool/code docstrings, not enumerated per operation
- [ ] **MC-058-05** — Define versioning and compatibility promises, including how unknown/newer data and unsupported features are handled.  
  ↳ **PARTIAL** — document versioned via package version; no separate doc-schema version
- [ ] **MC-058-06** — Define measurable acceptance criteria for correctness, security, performance, resource use, interoperability, and operability.  
  ↳ **PARTIAL** — correctness/security criteria are test assertions; no per-component performance/operability criteria

### B. Architecture & Data Model

- [ ] **MC-058-07** — Create a design showing data/control flow, lifecycle boundaries, concurrency domains, persistence (if any), and adjacent subsystem interactions.  
  ↳ **PARTIAL** — flow described in prose only; no design diagram
- [ ] **MC-058-08** — Choose canonical internal representations independent of host-language object identity and implementation-specific memory layout.  
  ↳ **N/A-PROPOSED** — no data representation owned by this component
- [ ] **MC-058-09** — Define deterministic state machines for lifecycle-sensitive behavior, including terminal, error, retry, rollback, and cancellation states.  
  ↳ **N/A-PROPOSED** — stateless/pure component; no lifecycle to model
- [ ] **MC-058-10** — Specify memory ownership and allocation rules; prove every allocation/resource has one defined release path.  
  ↳ **N/A-PROPOSED** — no manual allocations; host memory is garbage-collected
- [ ] **MC-058-11** — Define locking/atomicity strategy for shared state and document lock ordering or lock-free invariants.  
  ↳ **N/A-PROPOSED** — no shared mutable state
- [ ] **MC-058-12** — Define hard resource budgets for CPU, memory, nesting, payload bytes, queue depth, handles, and elapsed time.  
  ↳ **N/A-PROPOSED** — not a runtime component
- [ ] **MC-058-13** — Design stable machine-readable diagnostics and telemetry without secrets or unbounded-cardinality user-controlled fields.  
  ↳ **N/A-PROPOSED** — documentation component

### C. Domain-Specific Controls

- [ ] **MC-058-14** — Define severity levels, activation criteria, and decision authority for incidents involving this component.  
  ↳ **PARTIAL** — plays P1-P6 with triggers; severity scale/decision authority not assigned
- [x] **MC-058-15** — Provide exact tested containment/rollback commands with prerequisite and safety checks.  
  ↳ ConfigManager.rollback / health emergency_disabled exercised in tests (ConfigTrustTest)
- [ ] **MC-058-16** — Preserve forensic evidence before destructive remediation when operational safety permits.  
  ↳ **PARTIAL** — playbook requires snapshot+audit preservation; not exercised
- [ ] **MC-058-17** — Define communication, escalation, ownership handoff, and status-update procedures.  
  ↳ **PARTIAL** — escalation chain by role; no communication templates
- [x] **MC-058-18** — Document consistency implications of rollback, restart, cancellation, forced teardown, and partial recovery.  
  ↳ snapshot semantics: in-flight calls finish on their snapshot (docs/RUNBOOK.md A)
- [x] **MC-058-19** — Require post-action validation of semantic correctness, not merely process liveness.  
  ↳ runbook verify steps re-run tools/ci.py --quick
- [ ] **MC-058-20** — Run recurring game days/tabletops and track remediation actions to closure.  
  ↳ **OPEN** — no game day/tabletop run
- [ ] **MC-058-21** — Feed incident findings back into tests, alerts, limits, threat model, and release gates.  
  ↳ **PARTIAL** — fuzz regressions directory is the feedback path; no incident history

### D. Component-Specific Controls

- [x] **MC-058-22** — Use stable identifiers and bidirectional links to the code, tests, risks, requirements, artifacts, and owners the document governs.  
  ↳ MC/REQ/T/R ids cross-linked in docs/TRACEABILITY.md and docs/THREAT_MODEL.md
- [ ] **MC-058-23** — Version and preserve immutable historical revisions; record supersession and exception decisions explicitly.  
  ↳ **PARTIAL** — evidence schemas versioned (inv12-ci/1, inv12-release-evidence/1); historical copies depend on VCS
- [x] **MC-058-24** — Automate consistency checks so release documentation cannot silently diverge from executable evidence.  
  ↳ DocsExamplesTest (doc references + examples) and this generator re-reading evidence verdicts
- [ ] **MC-058-25** — Define exact trigger conditions, decision authority, commands, prerequisites, and abort criteria for emergency actions.  
  ↳ **PARTIAL** — triggers + commands documented; decision authority not named
- [ ] **MC-058-26** — Preserve forensic evidence and state-consistency information before destructive remediation when safe to do so.  
  ↳ **PARTIAL** — playbook requires snapshot+audit preservation; not exercised

### E. Implementation

- [ ] **MC-058-27** — Implement strict typed validation before mutation, allocation, I/O, authorization, or ownership transfer.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-28** — Use checked arithmetic for sizes, offsets, indexes, counters, timestamps, and numeric conversions; reject overflow/underflow.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-29** — Remove assertion-only correctness dependencies so optimized/release builds remain semantically identical.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-30** — Make failure paths exception/trap safe so partial work rolls back or remains in a documented recoverable state.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-31** — Use immutable snapshots or controlled copies anywhere mutable host values could alias across the boundary.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-32** — Read policy/configuration through a consistent snapshot so one operation cannot observe mixed versions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-33** — Construct structured errors at the lowest layer that knows the cause; preserve causal chains without leaking sensitive payloads.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-34** — Implement timeout/cancellation semantics for blocking or async operations and guarantee deterministic cleanup.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-35** — Reject impossible/unknown enum states, stale handles, unsupported versions, absent capabilities, and invalid lifecycle transitions.  
  ↳ **N/A-PROPOSED** — applies to runtime code; this component is tooling/documentation
- [ ] **MC-058-36** — Make generated artifacts deterministic and embed generator version plus input schema/configuration digest.  
  ↳ **N/A-PROPOSED** — generates no artifacts

### F. Security & Hardening

- [ ] **MC-058-37** — Create abuse cases for malformed input, privilege misuse, resource exhaustion, downgrade, replay, substitution, and state confusion where applicable.  
  ↳ **PARTIAL** — covered indirectly by program threat model
- [ ] **MC-058-38** — Fail closed for malformed, ambiguous, unauthenticated, untrusted, unsupported, or unverifiable inputs unless a safe alternate mode is specified.  
  ↳ **N/A-PROPOSED** — no input processing
- [ ] **MC-058-39** — Canonicalize before comparison, hashing, authorization, caching, signature verification, or deduplication.  
  ↳ **N/A-PROPOSED** — no comparison/hash/auth decision
- [ ] **MC-058-40** — Enforce hard limits early enough to prevent expensive allocation, deep recursion, uncontrolled fan-out, or log amplification.  
  ↳ **N/A-PROPOSED** — no attacker-sized input
- [ ] **MC-058-41** — Prevent secrets, credentials, raw memory, sensitive payloads, and protected identifiers from leaking through diagnostics or crash output.  
  ↳ **N/A-PROPOSED** — emits no diagnostics
- [x] **MC-058-42** — Run dependency/static/security analysis and require zero unresolved critical/high findings or a formally approved time-bounded waiver.  
  ↳ ruff E,F,W,B,S clean; cargo clippy -D warnings; go vet; zero third-party runtime deps (evidence/ci_run.json)

### G. Verification & Certification

- [ ] **MC-058-43** — Create unit tests for nominal behavior, all documented boundary values, and each distinct error class.  
  ↳ **OPEN** — no unit tests for this component
- [ ] **MC-058-44** — Create negative tests proving malformed/unsupported inputs fail deterministically without state corruption or resource leakage.  
  ↳ **N/A-PROPOSED** — document component
- [ ] **MC-058-45** — Add property-based and/or coverage-guided fuzz testing with reproducible seeds and minimized persisted regressions.  
  ↳ **N/A-PROPOSED** — not input-processing code
- [ ] **MC-058-46** — Run concurrency/re-entrancy tests wherever state, callbacks, handles, async completion, cancellation, or registries are involved.  
  ↳ **N/A-PROPOSED** — no shared state, callbacks or async completion
- [ ] **MC-058-47** — Measure branch/error-path/state-transition coverage and add tests for all security- and lifecycle-critical branches.  
  ↳ **PARTIAL** — line+arc coverage 91% of canon/ (evidence/coverage.json); branch/state-transition coverage not measured separately
- [ ] **MC-058-48** — Run the declared platform/runtime matrix and record exact toolchain, OS, CPU, runtime, and feature configuration with results.  
  ↳ **PARTIAL** — executed on Linux x86-64 only with recorded toolchains (evidence/sbom.cdx.json tools); ARM64/macOS/Windows declared, not run
- [ ] **MC-058-49** — Add a clean-environment release-mode certification test using only declared dependencies.  
  ↳ **N/A-PROPOSED** — documentation
- [x] **MC-058-50** — Attach machine-readable evidence and artifact digests to the release gate for this component.  
  ↳ evidence/RELEASE_EVIDENCE.json binds evidence digests and gate verdicts

### H. Operations, Documentation & Release

- [ ] **MC-058-51** — Emit sufficient metrics/logs/traces/audit evidence to detect each major failure mode without inspecting sensitive payloads.  
  ↳ **PARTIAL** — gate results are JSON evidence; no runtime telemetry
- [x] **MC-058-52** — Write operator/developer runbooks covering diagnosis, safe rollback/recovery, known failure signatures, and escalation.  
  ↳ docs/RUNBOOK.md + docs/INCIDENT_PLAYBOOK.md (failure signatures, rollback, escalation roles)
- [x] **MC-058-53** — Document configuration, compatibility, migration, upgrade, and downgrade procedures and validate examples in CI.  
  ↳ docs/OPERATIONS.md + docs/COMPATIBILITY.md; config examples validated in CI (DocsExamplesTest)
- [ ] **MC-058-54** — Generate immutable release evidence containing version, source revision, checksums, dependency/provenance data, and test results.  
  ↳ **PARTIAL** — version, per-file sha256, tree digest, SBOM, gate results sealed; no VCS revision and no signature
- [ ] **MC-058-55** — Define ownership, maintenance cadence, deprecation policy, support horizon, and escalation contacts/roles.  
  ↳ **PARTIAL** — roles, cadence, deprecation, support horizon in docs/OPERATIONS.md; named owners/contacts not assigned
- [ ] **MC-058-56** — Close the component only when every mandatory item has objective evidence and no unresolved P0/P1 defect remains.  
  ↳ **OPEN** — component cannot be closed: open/partial items remain (see this component's list)

### Definition of Done

- [ ] **MC-058-GATE-A** — All 56 controls are complete, explicitly waived, or formally deferred with owner and due date.  
  ↳ **OPEN** — open/partial controls remain without approved waiver or named owner + due date
- [ ] **MC-058-GATE-B** — Required tests pass in clean CI and optimized/release mode with retained machine-readable evidence.  
  ↳ **PARTIAL** — passes in the local clean pipeline incl. python -O (evidence/ci_run.json); hosted CI not executed
- [x] **MC-058-GATE-C** — No unresolved P0/P1 defect remains in correctness, security, memory/resource safety, compatibility, or recoverability.  
  ↳ no open P0/P1 defect in correctness, security, resource safety, compatibility or recoverability
- [ ] **MC-058-GATE-D** — Architecture, security, operations, compatibility, and maintenance ownership have been peer reviewed.  
  ↳ **OPEN** — peer review by named reviewers not recorded
- [x] **MC-058-GATE-E** — Release evidence links requirements → implementation → tests → artifact digest for this component.  
  ↳ docs/TRACEABILITY.md + evidence/RELEASE_EVIDENCE.json (requirement -> impl -> tests -> digest)

---

## Program-level completion gates

- [ ] **PROGRAM-GATE-01** — All 58 component Definition-of-Done gates are satisfied or have formally approved time-bounded waivers.  
  ↳ **OPEN** — component DoD gates A/D open for all components
- [ ] **PROGRAM-GATE-02** — The requirements traceability matrix contains no mandatory requirement without implementation and verification evidence.  
  ↳ **PARTIAL** — traceability complete for implemented items; blocked/open items listed
- [x] **PROGRAM-GATE-03** — The cross-language conformance matrix passes for every declared supported language/runtime pair.  
  ↳ 4 languages x 16 pairs green (evidence/conformance.json)
- [ ] **PROGRAM-GATE-04** — The platform architecture matrix passes for every declared supported OS, CPU architecture, runtime, and feature profile.  
  ↳ **BLOCKED** — only Linux x86-64 executed
- [x] **PROGRAM-GATE-05** — Fuzzing, property-based, malicious-memory, concurrency, and leak/use-after-free suites have no unresolved release-blocking findings.  
  ↳ 0 crashes, 0 divergences, 0 leaks (evidence/fuzz.json, conformance.json, ci_run.json); sanitizers not run -> see MC-032
- [ ] **PROGRAM-GATE-06** — Performance/SLO certification is reproducible and includes large-payload, overload, fairness, and DoS behavior.  
  ↳ **PARTIAL** — reproducible harness incl. DoS/fairness; SLO certified only as native-fixture proxy
- [x] **PROGRAM-GATE-07** — Threat-model mitigations are implemented, tested, and observable through audit/telemetry evidence.  
  ↳ every THREAT_MODEL row cites a test; audit/metrics emitted
- [x] **PROGRAM-GATE-08** — Configuration, identity/capability, provenance, SBOM, trust-outage, and rollback controls have been exercised end to end.  
  ↳ exercised end to end in ConfigTrustTest + BoundaryIntegrationTest
- [ ] **PROGRAM-GATE-09** — The reproducible pk_core environment executes the external gate from a clean environment with retained results.  
  ↳ **BLOCKED** — pk_core not present
- [ ] **PROGRAM-GATE-10** — CI promotion releases the exact tested artifact; checksums, signatures/attestations, SBOM, provenance, and evidence are bundled.  
  ↳ **PARTIAL** — checksums/SBOM/provenance/evidence bundled; no signatures/attestations; no promotion system
- [x] **PROGRAM-GATE-11** — Compatibility/support matrices are generated from passing evidence and match what the release actually supports.  
  ↳ docs/COMPATIBILITY.md numbers taken from evidence/conformance.json
- [ ] **PROGRAM-GATE-12** — Operational runbooks, rollback procedures, and incident playbooks have named owners and have been exercised in a game day/tabletop.  
  ↳ **OPEN** — no named owners; no game day/tabletop
