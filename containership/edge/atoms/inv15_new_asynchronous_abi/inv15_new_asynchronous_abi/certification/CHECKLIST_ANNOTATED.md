# INV-15 New Asynchronous ABI v4.2.0 — Professional Component Checklists

**Purpose:** Engineering implementation, hardening, verification, certification, and release checklist for all 72 missing components identified after the INV-15 v4.2.0 hardening pass.

**Checklist convention:**
- `[ ]` = not yet verified; `[x]` = verified with linked evidence.
- **P0** = release-blocking correctness/security/runtime foundation.
- **P1** = required production integration/operability item; may be sequenced after core P0 implementation but must close before general-availability sign-off unless formally waived.
- Every checked item should have reproducible evidence: source revision, test artifact, benchmark, ADR/spec, dashboard, or signed release record.

## Global Definition of Done
- [ ] All 72 component sections have an assigned owner, reviewer, target release, and linked evidence. — **BLOCKED** (B: no owners/reviewers)
- [ ] All P0 checklist items are complete; any exception has a named risk owner, explicit scope, compensating control, expiration date, and approval record. — **BLOCKED** (B: P0 items remain open)
- [ ] Wire/IDL artifacts and generated bindings are versioned, reproducible, and pass the shared conformance corpus. — **EVIDENCED**
- [ ] Lifecycle semantics are deterministic for completion, take, wait, cancel, timeout, trap, abandon, teardown, and restart. — **PARTIAL** (P: deterministic in the reference host; restart only as a model)
- [ ] No correctness or security guarantee depends on debug assertions, Python-only reference behavior, or undefined scheduler timing. — **BLOCKED** (B: guarantees depend on the Python reference by construction)
- [ ] All resource dimensions are bounded and accounted: handles, live entries, ready entries, waiters, tombstones, payload bytes, queues, telemetry buffers, retries, and cancellation metadata. — **PARTIAL** (P: all dimensions bounded; payload accounting understates heap ~4.5x)
- [ ] Cross-tenant and cross-instance handle substitution, replay, stale-handle use, and forged-handle attempts are rejected and covered by adversarial tests. — **EVIDENCED**
- [ ] Lost-wakeup, concurrency-race, soak, overload, fuzz, fault-injection, and independent conformance suites pass on the release matrix. — **PARTIAL** (P: suites pass at CI scale; independent conformance BLOCKED)
- [ ] Metrics, traces, logs, debug endpoints, dashboards, and alerts are secret-safe and validated under overload/exporter failure. — **PARTIAL** (P: secret-safety tested; overload/exporter failure not)
- [ ] Performance baselines and regression thresholds are recorded for supported architectures/runtimes, including p50/p95/p99 and worst-case where specified. — **PARTIAL** (P: one architecture/runtime)
- [ ] Supply-chain provenance, SBOM, dependency locks, signatures, and artifact digests are attached to the release. — **PARTIAL** (P: SBOM/digests yes, signatures no)
- [ ] Canary, rollback, emergency drain/disable, restart, and incident procedures have been exercised against the candidate release. — **PARTIAL** (P: procedures and hooks tested as code, not exercised on a fleet)
- [ ] Compatibility matrices and migration behavior for INV-11/12/14/16/17/18, SCH-01, and host runtimes are published and enforced. — **PARTIAL** (P: adjacent layers absent)
- [ ] Documentation describes public semantics, error codes, lifecycle, operational controls, SLOs, limitations, and upgrade/rollback requirements. — **PARTIAL** (P: package-level docs)
- [ ] Final release sign-off includes ABI/runtime engineering, security, performance/reliability, and operations/SRE approval. — **BLOCKED** (B: sign-off needs four named functions)

# A. ABI specification and wire contract

## 1. Canonical WIT/IDL definition for `PK_ASYNC_CALL/1`

**Objective:** Implement and certify **Canonical WIT/IDL definition for `PK_ASYNC_CALL/1`** so that typed function signatures, discriminated immediate/subtask result, stable field numbering, version negotiation, and canonical encoding rules.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define the exact `PK_ASYNC_CALL/1` signature, including argument list, result union, immediate-success/immediate-error/subtask variants, and handle type. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Specify when the host is allowed to return an immediate result versus a subtask and require callers to treat both paths as semantically equivalent. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Define the call-admission failure path separately from callee execution failure so refused work cannot be confused with an asynchronously completed error. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Verify generated bindings preserve discriminants and payload layouts across all supported languages and runtimes. — **BLOCKED** (B: only one language (Python) and one runtime exist)
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestIdl, test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 2. Canonical WIT/IDL definition for `PK_WAITABLE_SET/1`

**Objective:** Implement and certify **Canonical WIT/IDL definition for `PK_WAITABLE_SET/1`** so that set construction, readiness result schema, ordering guarantees, duplicate semantics, maximum cardinality, and invalid-handle behavior.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define wait-set construction semantics for empty sets, singleton sets, duplicates, foreign handles, stale handles, and sets at maximum cardinality. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] State whether readiness ordering is insertion order, completion order, priority order, unspecified, or fairness-governed; test the chosen rule. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Define whether one readiness result consumes, snapshots, or merely reports readiness and how repeated waits on the same ready handle behave. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Prove the maximum cardinality is enforced before resource allocation large enough to create a denial-of-service condition. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCore, test_wire.TestNegotiation
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 3. Canonical WIT/IDL definition for `PK_SUBTASK_CANCEL/1`

**Objective:** Implement and certify **Canonical WIT/IDL definition for `PK_SUBTASK_CANCEL/1`** so that cancellation request, acknowledgment state, reason code, already-complete semantics, and idempotency rules.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define cancellation request and acknowledgment records with stable states such as requested, accepted, already-complete, unable-to-cancel, and invalid-handle. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Specify idempotency for repeated cancellation of the same subtask and guarantee repeated requests do not create duplicate side effects. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Define the winner and observable state for cancel-versus-complete races at the exact linearization boundary. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Verify cancellation reasons are bounded identifiers and are not trusted as arbitrary host log strings. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCancellation, test_certification.TestRaces
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 4. Machine-readable error envelope

**Objective:** Implement and certify **Machine-readable error envelope** so that stable numeric/string error codes for not-ready, foreign/forged handle, consumed handle, budget exhaustion, timeout, cancellation, trap, host failure, and unsupported version.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Allocate stable numeric and symbolic error identifiers and publish a registry with ownership, severity/class, retryability, and compatibility rules. — **PARTIAL** (P: registry has code+retryable but no owner/severity class; categories are distinct codes not a published class taxonomy; envelope carries no causal chain) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Separate caller errors, resource refusal, lifecycle errors, timeout/cancellation, guest trap, host failure, and protocol/version errors into non-overlapping classes. — **PARTIAL** (P: registry has code+retryable but no owner/severity class; categories are distinct codes not a published class taxonomy; envelope carries no causal chain) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Specify whether auxiliary fields are safe to expose across trust boundaries and prohibit secrets, raw handles, stack dumps, or host filesystem data. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Add round-trip tests proving errors survive lowering/lifting without loss of code, category, causal chain, or safe diagnostic context. — **PARTIAL** (P: registry has code+retryable but no owner/severity class; categories are distinct codes not a published class taxonomy; envelope carries no causal chain) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestIdl, test_security_telemetry.TestRedaction
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 5. Opaque-handle binary representation

**Objective:** Implement and certify **Opaque-handle binary representation** so that fixed-width or canonical variable-width encoding for token/sequence, endianness, serialization, redaction, and parsing rules.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Choose and freeze the opaque handle bit layout or canonical variable-width encoding; define token bits, generation/epoch bits if any, and reserved space. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Require constant-length or bounded parsing with explicit rejection of truncated, overlong, non-canonical, and unsupported encodings. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define byte order and canonical textual/debug representation; the textual form must be redacted or non-authoritative and never be accepted as a capability unless explicitly designed. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Test serialization/deserialization across architectures with different native endianness and word size. — **BLOCKED** (B: layout is explicit big-endian but was only executed on one little-endian x86_64 host)
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 6. Handle version tag / feature bits

**Objective:** Implement and certify **Handle version tag / feature bits** so that forward-compatible decoding and explicit rejection of unsupported handle formats.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define handle format version bits independently from ABI protocol version so handle decoding can evolve without ambiguous interpretation. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Reserve feature bits with a mandatory unknown-bit policy and require downgrade only when semantics remain safe. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Ensure older runtimes reject unsupported critical features before dereferencing or looking up the handle. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add vectors for every supported/unsupported version and feature-bit combination. — **PARTIAL** (P: vectors cover version 0/1/2, bit1 and bit4, not every flag combination) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestHandleEncoding, test_wire.TestVectors
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 7. Formal lifecycle state machine specification

**Objective:** Implement and certify **Formal lifecycle state machine specification** so that pending, ready, cancelled, consumed, abandoned, trapped, timed-out, and host-invalidated transitions with forbidden edges.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Publish a state-transition table for pending, ready, cancelled, consumed, abandoned, trapped, timed-out, and host-invalidated states. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Identify terminal states and prove no operation can resurrect a terminal handle or transition back to pending. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Specify exactly which operations are legal from each state and the error returned for every forbidden edge. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Model-check or property-test the lifecycle so every reachable state satisfies single-completion, single-consume, and reclamation invariants. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestLifecycle, test_certification.TestProperty
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 8. Conformance vectors

**Objective:** Implement and certify **Conformance vectors** so that known-good and known-bad encoded calls, waits, cancellations, handles, and failure envelopes for every implementation.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Create versioned binary fixtures for valid and invalid calls, handles, waits, cancellations, errors, and lifecycle sequences. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Include boundary vectors for zero/min/max integers, maximum payload/set sizes, unknown fields, unknown variants, truncation, trailing bytes, and non-canonical encodings. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Require every language/runtime implementation to consume the same vector corpus without local reinterpretation. — **BLOCKED** (B: only one language consumes the corpus; P: corpus hashed in MANIFEST, not signed)
- [ ] Sign or hash the conformance corpus and publish the corpus version in certification evidence. — **PARTIAL** (B: only one language consumes the corpus; P: corpus hashed in MANIFEST, not signed) · evidence: test_wire.TestVectors
- [ ] Freeze a normative schema/IDL artifact in source control and make generated bindings reproducible from that artifact with no hand-edited generated code. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Assign stable numeric discriminants, field identifiers, and variant tags; reserve extension ranges and document which values are permanently forbidden from reuse. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Define canonical encoding/decoding behavior for every field, including integer width, signedness, byte order, optionality, padding/alignment, unknown fields, and malformed input. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Specify version negotiation at the boundary: supported major/minor ranges, feature discovery, downgrade behavior, hard-fail behavior, and telemetry for incompatibility. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestVectors
- [ ] Document all normative invariants in RFC-style MUST/SHOULD/MAY language and link each invariant to at least one executable conformance test. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Prove round-trip stability across at least two independently generated bindings and require byte-for-byte canonical encoding where canonicalization is claimed. — **PARTIAL** (P: no incompatibility telemetry counter; the two codecs are hand-written by one author, not independently generated bindings) · evidence: test_wire.TestVectors
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestVectors
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_wire.TestVectors
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_wire.TestVectors
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestVectors
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestVectors
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# B. Timing, cancellation, and backpressure semantics

## 9. Deadline propagation

**Objective:** Implement and certify **Deadline propagation** so that absolute/relative deadline representation, host clock source, overflow handling, and inheritance across nested async calls.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Choose a canonical deadline representation and state whether deadlines are absolute monotonic ticks, relative durations, or a paired representation. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define deadline inheritance and min(parent, child) behavior for nested calls, plus explicit opt-out/detachment semantics. — **PARTIAL** (P: detachment does not opt out of deadline inheritance; no cross-binding rounding exists; scheduler suspension not tested) · evidence: test_host.TestDeadlines
- [ ] Handle duration overflow/underflow and conversion rounding deterministically across language bindings. — **PARTIAL** (P: detachment does not opt out of deadline inheritance; no cross-binding rounding exists; scheduler suspension not tested) · evidence: test_host.TestDeadlines
- [ ] Test deadline propagation through scheduler suspension, nested fan-out, cancellation, and host clock anomalies. — **PARTIAL** (P: detachment does not opt out of deadline inheritance; no cross-binding rounding exists; scheduler suspension not tested) · evidence: test_host.TestDeadlines
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDeadlines
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDeadlines
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDeadlines
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestDeadlines
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestDeadlines
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestDeadlines
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestDeadlines
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestDeadlines
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 10. Timeout behavior

**Objective:** Implement and certify **Timeout behavior** so that distinction between wait timeout, call timeout, deadline expiry, and cancellation; exact post-timeout handle state.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define separate codes and state transitions for wait timeout, call timeout, inherited deadline expiry, and explicit cancellation. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Specify whether a wait timeout leaves the subtask live and waitable, and prove a later completion can still be observed safely. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define precedence when timeout/deadline/cancellation/completion become observable in the same scheduling quantum. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Test repeated timeouts without leaking wait registrations, references, or scheduler wakeups. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDeadlines
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDeadlines
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDeadlines
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestDeadlines
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestDeadlines
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestDeadlines
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestDeadlines
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestDeadlines
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestDeadlines
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 11. Cancellation acknowledgment protocol

**Objective:** Implement and certify **Cancellation acknowledgment protocol** so that observable states for requested, accepted, propagated, completed-before-cancel, and unable-to-cancel.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define the full cancellation acknowledgment finite-state machine and whether acknowledgment is synchronous, asynchronous, or both. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Make clear whether `accepted` means merely recorded, delivered to callee, or guaranteed to stop further side effects. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Provide a terminal acknowledgment for unable-to-cancel and completed-before-cancel without misreporting success. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Measure and expose cancellation-request-to-acknowledgment and request-to-terminal-state latency. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCancellation
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCancellation
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCancellation
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCancellation
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCancellation
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 12. Cancellation cause taxonomy

**Objective:** Implement and certify **Cancellation cause taxonomy** so that bounded stable reason codes rather than free-form strings at the ABI boundary.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Publish a bounded cancellation reason registry with reserved vendor/private ranges and stable semantic meanings. — **PARTIAL** (N: v1 decoders REJECT unknown reason codes (MALFORMED) instead of mapping them to OTHER - not forward-compatible; P: no vendor range; only Future.cancel is mapped) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Define mappings from language/runtime cancellation exceptions into the bounded ABI reason taxonomy. — **PARTIAL** (N: v1 decoders REJECT unknown reason codes (MALFORMED) instead of mapping them to OTHER - not forward-compatible; P: no vendor range; only Future.cancel is mapped) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Ensure unknown future reason codes remain forward-compatible and do not crash older consumers. — **NOT_DONE** (N: v1 decoders REJECT unknown reason codes (MALFORMED) instead of mapping them to OTHER - not forward-compatible; P: no vendor range; only Future.cancel is mapped)
- [ ] Prevent user-controlled reason text from entering high-cardinality metrics or privileged logs. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCancellation, test_wire.TestIdl
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 13. Nested cancellation tree

**Objective:** Implement and certify **Nested cancellation tree** so that parent/child subtask propagation and deterministic handling of detached child work.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Model parent/child links explicitly and define whether cancellation propagation is depth-first, breadth-first, batched, or scheduler-defined. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define detached-child ownership and lifetime so parent teardown cannot orphan unaccounted work. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Prevent cancellation cycles or invalid ancestry relationships and test deep/wide trees under quota pressure. — **PARTIAL** (P: deep tree tested (64 levels); wide trees under quota pressure not tested) · evidence: test_host.TestCancellation
- [ ] Ensure budget/accounting release is correct for partially cancelled trees and children that complete during propagation. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestCancellation
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCancellation
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCancellation
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCancellation
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCancellation
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCancellation
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCancellation
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 14. Idempotency metadata

**Objective:** Implement and certify **Idempotency metadata** so that call identifiers or keys allowing safe retry where the invoked operation supports it.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define idempotency-key format, scope, entropy/uniqueness expectations, retention window, and tenant/operation binding. — **PARTIAL** (N: same-key/different-payload conflict is not detected (payload is not compared); P: no entropy guidance; callee retry safety not declared per operation) · evidence: test_host.TestIdempotency
- [ ] State which operations support idempotency and prohibit callers from assuming retry safety when the callee contract does not declare it. — **PARTIAL** (N: same-key/different-payload conflict is not detected (payload is not compared); P: no entropy guidance; callee retry safety not declared per operation) · evidence: test_host.TestIdempotency
- [ ] Define duplicate-key behavior for same payload versus conflicting payload and expose a stable conflict error. — **NOT_DONE** (N: same-key/different-payload conflict is not detected (payload is not compared); P: no entropy guidance; callee retry safety not declared per operation)
- [ ] Protect idempotency metadata from cross-tenant replay and unbounded retention. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestIdempotency
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestIdempotency
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestIdempotency
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestIdempotency
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestIdempotency
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestIdempotency
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestIdempotency
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestIdempotency
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 15. Retry contract

**Objective:** Implement and certify **Retry contract** so that explicit statement that retry is host/caller policy, plus the metadata required to prevent duplicate execution.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Document retry as caller/host policy rather than implicit ABI behavior; the ABI must not silently re-execute completed or uncertain operations. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Specify retryable error classes and distinguish safe retry from unknown-commit/ambiguous outcome cases. — **PARTIAL** (N: attempt number is not carried; no retry-storm test; P: ambiguous-commit outcome not distinguished) · evidence: test_host.TestIdempotency
- [ ] Carry attempt number, idempotency metadata, original deadline, and causal trace context across retries. — **NOT_DONE** (N: attempt number is not carried; no retry-storm test; P: ambiguous-commit outcome not distinguished)
- [ ] Test retry storms with exponential/backoff policy supplied by the host and verify quotas/fairness still hold. — **NOT_DONE** (N: attempt number is not carried; no retry-storm test; P: ambiguous-commit outcome not distinguished)
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestIdempotency
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestIdempotency
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestIdempotency
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestIdempotency
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestIdempotency
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestIdempotency
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestIdempotency
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestIdempotency
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestIdempotency
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 16. Hierarchical budgets

**Objective:** Implement and certify **Hierarchical budgets** so that instance, workload, tenant, process, node, and global outstanding-call ceilings.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define ceilings at instance, workload, tenant, process, node, and global scopes with deterministic precedence when multiple scopes are exhausted. — **PARTIAL** (P: node/global scopes collapse into process; explain() shows tenant names to operators (not reviewed)) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Make reservations and releases atomic so failures cannot leak budget and concurrent admission cannot oversubscribe a ceiling. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Expose budget utilization and refusal reason by scope without leaking other tenants' identities or exact consumption. — **PARTIAL** (P: node/global scopes collapse into process; explain() shows tenant names to operators (not reviewed)) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Test recovery after sustained exhaustion and verify capacity returns after completion, cancel, abandon, teardown, and crash cleanup. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 17. Fairness policy hooks

**Objective:** Implement and certify **Fairness policy hooks** so that per-tenant/per-workload admission classes or scheduler hints preventing one workload from monopolizing waitable capacity.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define scheduler hint fields, allowed ranges, default class, validation, and whether hints are advisory or enforceable. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Prevent user-controlled priority from bypassing tenant quotas or causing starvation of default-class work. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Measure fairness with bounded starvation metrics under mixed tenants/workloads and adversarial priority patterns. — **PARTIAL** (P: fairness measured as held-count parity, no starvation metric) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Provide a policy-disabled baseline in which correctness does not depend on any scheduler hint. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestBudgetsFairness, test_certification.TestSoakOverload
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 18. Drain/quiesce mode

**Objective:** Implement and certify **Drain/quiesce mode** so that stop-admitting-new-work while allowing or cancelling existing subtasks during upgrade/shutdown.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define state transition from accepting to quiescing to drained/terminated and make admission refusal deterministic during each phase. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Provide configurable policy for live work: allow-to-complete, bounded grace period, cancel, or force-invalidate after deadline. — **PARTIAL** (P: no bounded grace-period timer; policies are allow/cancel/invalidate) · evidence: test_host.TestDrainDisable
- [ ] Ensure late completions after drain/teardown cannot resurrect handles or mutate a new instance epoch. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Expose drain progress, remaining live counts, oldest age, cancellation counts, and blockers to operators. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Define the authoritative clock and time domain for the component, including monotonic versus wall-clock use, resolution, wraparound/overflow behavior, suspend/resume effects, and cross-thread visibility. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Specify race semantics for completion, timeout, cancellation, retry, teardown, and admission occurring concurrently; every race must resolve to one deterministic externally observable state. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Define propagation semantics across nested calls, including inheritance, override rules, detachment, fan-out/fan-in behavior, and cleanup of descendants. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDrainDisable
- [ ] Bound all queues, counters, reason/value domains, and retry/admission paths so hostile or accidental load cannot create unbounded memory or CPU growth. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Define idempotency and duplicate-suppression requirements wherever an operation may be retried, replayed, cancelled late, or completed after caller abandonment. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDrainDisable
- [ ] Expose scheduler/admission hooks without embedding policy in the ABI; policy inputs must be explicit, bounded, versioned, and ignorable by older implementations when safe. — **PARTIAL** (P: fan-out/fan-in propagation unwritten; duplicate-suppression only via idempotency keys; hooks are not version-tagged) · evidence: test_host.TestDrainDisable
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestDrainDisable
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestDrainDisable
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestDrainDisable
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestDrainDisable
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestDrainDisable
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# C. Host waitable-table implementation

## 19. Production host-side table backend

**Objective:** Implement and certify **Production host-side table backend** so that replacement for the in-process Python reference map using runtime-native memory/accounting primitives.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Select the production table data structure and allocator with explicit O(1) or bounded-complexity targets for allocate, lookup, ready, consume, cancel, and invalidate. — **BLOCKED** (B: the production backend is by definition not this Python reference; nothing here replaces it)
- [ ] Shard or partition synchronization to avoid a single global lock becoming a scheduler-scale bottleneck. — **BLOCKED** (B: the production backend is by definition not this Python reference; nothing here replaces it)
- [ ] Ensure table entries store only the minimum metadata required for lifecycle, accounting, ownership, and payload references. — **PARTIAL** (B: the production backend is by definition not this Python reference; nothing here replaces it)
- [ ] Run memory and contention profiling at maximum supported concurrency and prove no unbounded scan exists on a hot path. — **BLOCKED** (B: the production backend is by definition not this Python reference; nothing here replaces it)
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **NOT_DONE** (no executed evidence)
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **NOT_DONE** (no executed evidence)
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **NOT_DONE** (no executed evidence)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **BLOCKED** (P: generated component dossier + SPEC, not a reviewed ADR)
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **BLOCKED** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **BLOCKED** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **BLOCKED** (P: COMPATIBILITY.md is package-level)
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **BLOCKED** (P: docs are package-level; no generated per-component reference)
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 20. Generation-safe handle registry

**Objective:** Implement and certify **Generation-safe handle registry** so that host-native slot/generation scheme or equivalent preventing stale-handle aliasing after slot reuse.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Encode generation or epoch with every reusable slot and validate both slot and generation before accepting a handle. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Define generation-wrap policy and prove wrap cannot make a stale handle valid within the supported process lifetime/threat model. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Clear or poison reclaimed slots before reuse so late producers cannot publish into a new occupant. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Stress slot reuse with forced tiny registries to accelerate wrap/reuse races during testing. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestGenerations
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestGenerations
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestGenerations
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestGenerations
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestGenerations
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestGenerations
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestGenerations
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 21. Cryptographically strong token source binding

**Objective:** Implement and certify **Cryptographically strong token source binding** so that platform RNG integration and failure policy if secure randomness is unavailable.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Use an OS/runtime cryptographic RNG with documented API, blocking/failure behavior, FIPS mode considerations where applicable, and fork/VM snapshot semantics. — **PARTIAL** (P: secrets.token_bytes documented, FIPS not considered; guessing math for deployment scale not written) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Define fail-closed behavior if secure randomness is unavailable; do not fall back to timestamps, counters, PRNG defaults, or predictable entropy. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Generate enough entropy to make handle guessing infeasible for the deployment scale and lifetime; document the collision probability analysis. — **PARTIAL** (P: secrets.token_bytes documented, FIPS not considered; guessing math for deployment scale not written) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Add fault injection for RNG failure and health-test the RNG integration without logging generated tokens. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestRng, test_certification.TestFaultInjection
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 22. Wakeup registration primitive

**Objective:** Implement and certify **Wakeup registration primitive** so that atomic subscribe/check sequence that proves no lost wakeup between readiness publication and wait registration.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Implement registration as an atomic check-and-subscribe or subscribe-and-recheck protocol with a proof that readiness cannot be missed in the race window. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Define waiter cancellation/removal semantics and ensure removing a waiter racing with publication cannot leak callbacks or double wake. — **PARTIAL** (B: no futex/scheduler-native primitive; P: thousands of randomized iterations, not millions; removal-vs-publication race not threaded) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Use scheduler-native primitives or futex/event equivalents that do not require polling guest state. — **BLOCKED** (B: no futex/scheduler-native primitive; P: thousands of randomized iterations, not millions; removal-vs-publication race not threaded)
- [ ] Run a targeted randomized interleaving test that covers publication before, during, and after waiter registration millions of times. — **PARTIAL** (B: no futex/scheduler-native primitive; P: thousands of randomized iterations, not millions; removal-vs-publication race not threaded) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestSubscribe, test_certification.TestLostWakeup
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 23. Ready-queue implementation

**Objective:** Implement and certify **Ready-queue implementation** so that lock-efficient/MPSC or scheduler-native delivery path instead of scanning a Python table.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Choose MPSC/MPMC/scheduler-native queue semantics that match producer/consumer topology and document memory-ordering requirements. — **BLOCKED** (B: no MPSC/scheduler-native queue; no multi-core contention measurement possible under the GIL)
- [ ] Bound the queue and define overflow policy that preserves correctness—never silently drop readiness notifications. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Deduplicate or safely tolerate repeated enqueue attempts for the same ready handle without unbounded queue growth. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Measure enqueue/dequeue contention and cache behavior under multi-core completion storms. — **BLOCKED** (B: no MPSC/scheduler-native queue; no multi-core contention measurement possible under the GIL)
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestReadyQueue, test_certification.TestSoakOverload
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 24. Batched readiness delivery

**Objective:** Implement and certify **Batched readiness delivery** so that bounded batch interface and fairness semantics for large ready sets.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define batch size minimum/default/maximum and whether callers may request fewer/more ready items. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Specify fairness across tenants, wait sets, and long-ready versus newly-ready entries when forming batches. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Ensure batching cannot starve a singleton waiter behind permanently busy producers. — **PARTIAL** (P: singleton-starvation not tested; N: no batch-size benchmark) · evidence: test_host.TestReadyQueue
- [ ] Benchmark throughput and tail latency across batch sizes and choose defaults from measured data. — **NOT_DONE** (P: singleton-starvation not tested; N: no batch-size benchmark)
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestReadyQueue
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestReadyQueue
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestReadyQueue
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestReadyQueue
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestReadyQueue
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestReadyQueue
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestReadyQueue
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 25. Completion publication API

**Objective:** Implement and certify **Completion publication API** so that runtime-facing producer interface with exactly-once completion/trap/cancel resolution.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define a producer API that resolves a subtask exactly once to success, typed error, trap, cancellation, timeout, or invalidation. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Reject duplicate publication deterministically and emit a diagnostic/audit signal without mutating the first terminal result. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Publish payload and terminal metadata before readiness with correct memory ordering. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Test producer death during publication and ensure consumers observe either the old valid state or the fully published terminal state—never partial data. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCore, test_certification.TestFaultInjection
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 26. Trap/fault completion state

**Objective:** Implement and certify **Trap/fault completion state** so that structured propagation when a callee traps, aborts, or the host terminates execution mid-subtask.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define structured trap/fault classes for guest trap, host abort, runtime panic, resource kill, dependency loss, and internal invariant failure. — **PARTIAL** (P: one TRAPPED class, host abort/resource kill not distinguished; no privileged diagnostic path; B: no language bindings) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Sanitize trap diagnostics crossing trust boundaries while retaining a privileged correlation path for operators. — **PARTIAL** (P: one TRAPPED class, host abort/resource kill not distinguished; no privileged diagnostic path; B: no language bindings) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] State whether a trap consumes the handle only on `take` or becomes terminal immediately while remaining inspectable. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Test trap propagation through every supported language binding and scheduler adapter. — **BLOCKED** (P: one TRAPPED class, host abort/resource kill not distinguished; no privileged diagnostic path; B: no language bindings)
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCore, test_adapters.TestAsyncFunction
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 27. Instance teardown invalidation

**Objective:** Implement and certify **Instance teardown invalidation** so that bulk invalidation of all handles and deterministic behavior for late completions after teardown.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Invalidate all instance-owned handles atomically or by epoch so no old handle is accepted after teardown begins. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Define behavior for waiters blocked on the instance at teardown and ensure they wake with a deterministic invalidated result. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Discard or safely account late producer completions after invalidation without touching freed memory. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Prove teardown reclaims table rows, payloads, wait registrations, queue entries, and accounting reservations. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestTeardownRestart
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestTeardownRestart
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestTeardownRestart
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestTeardownRestart
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestTeardownRestart
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestTeardownRestart
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 28. Runtime restart semantics

**Objective:** Implement and certify **Runtime restart semantics** so that explicit invalidation, reconstruction, or migration behavior across host process restarts.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define whether live handles are always invalid across restart or whether durable reconstruction is explicitly supported; default to invalidation unless persistence is designed. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Persist an instance/runtime epoch if serialized handles can survive process boundaries and reject pre-restart epochs. — **PARTIAL** (P: epoch is in memory, not persisted; crash at every transition not tested) · evidence: test_host.TestTeardownRestart
- [ ] Define restart recovery for accounting/tombstone metadata so stale external state cannot consume new capacity indefinitely. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Test crash/restart at each lifecycle transition and verify deterministic post-restart behavior. — **PARTIAL** (P: epoch is in memory, not persisted; crash at every transition not tested) · evidence: test_host.TestTeardownRestart
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestTeardownRestart
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestTeardownRestart
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestTeardownRestart
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestTeardownRestart
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestTeardownRestart
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestTeardownRestart
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestTeardownRestart
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 29. Memory accounting

**Objective:** Implement and certify **Memory accounting** so that per-row byte accounting, payload ownership rules, tombstone memory accounting, and hard ceilings.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Specify per-entry fixed overhead, variable payload accounting, waiter/queue metadata, tombstone bytes, allocator overhead assumptions, and accounting granularity. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Charge memory to the correct instance/workload/tenant before allocation and roll back atomically on failure. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Set hard and soft thresholds with telemetry, refusal behavior, and operator visibility; soft limits must not be mistaken for safety limits. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Run leak tests that reconcile logical counters with allocator/heap observations after large churn workloads. — **PARTIAL** (P: reconciliation ran and FOUND a gap - declared 256 B/row vs ~1.1 KB/row measured by tracemalloc (see BENCHMARK_BASELINE.json)) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestMemoryOwnership, test_certification.TestSoakOverload
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 30. Payload ownership/zero-copy contract

**Objective:** Implement and certify **Payload ownership/zero-copy contract** so that who owns returned buffers/resources, when ownership transfers, and safe reclamation after cancel/abandon.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define ownership for input buffers, result buffers, borrowed views, host resources, and language-managed objects at every transition. — **PARTIAL** (P: result ownership defined, input buffers not; B: sanitizers do not apply to CPython) · evidence: test_host.TestMemoryOwnership
- [ ] Specify zero-copy eligibility, alignment/lifetime constraints, pinning requirements, and when a copy is mandatory for safety. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Ensure cancellation/abandon/teardown cannot free memory still visible to a producer or consumer. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Use sanitizer/Miri/ASAN-equivalent tooling where applicable to validate lifetime and double-free/use-after-free safety. — **BLOCKED** (P: result ownership defined, input buffers not; B: sanitizers do not apply to CPython)
- [ ] Use runtime-native synchronization and allocation primitives appropriate to the production host; the reference Python map/locks must not be treated as the production concurrency design. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Document linearization points for allocation, readiness publication, wait registration, take/consume, cancellation, invalidation, and reclamation. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Prove memory safety and stale-reference safety under slot reuse, late completion, teardown, process restart, and concurrent access from multiple producer/consumer threads. — **BLOCKED** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only)
- [ ] Ensure all producer-to-consumer state publication has an explicit memory-ordering model; document acquire/release or equivalent happens-before guarantees. — **PARTIAL** (B: runtime-native primitives and a memory-safety proof need a production host; P: memory-ordering documented for the lock model only) · evidence: test_host.TestMemoryOwnership
- [ ] Bound memory with hard quotas for live entries, ready entries, tombstones, waiters, payload bytes, and per-tenant/per-instance accounting. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Instrument every state transition needed to debug leaks, duplicate completion, lost wakeups, stuck-ready entries, and invalid-handle access without logging secret handle material. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestMemoryOwnership
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestMemoryOwnership
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestMemoryOwnership
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestMemoryOwnership
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestMemoryOwnership
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestMemoryOwnership
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# D. Scheduler and adjacent-layer integration

## 31. SCH-01 scheduler adapter

**Objective:** Implement and certify **SCH-01 scheduler adapter** so that translate ready-table events into runnable component instances without polling or blocked guest stacks.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Map ready-table events to scheduler runnable entities with no polling loop and no blocked guest stack per suspended subtask. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Coalesce redundant wakeups without losing progress and define scheduler behavior when many handles for one instance become ready simultaneously. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Preserve tenant/workload fairness and priority hints while preventing wakeup storms from monopolizing scheduler queues. — **PARTIAL** (P: adapter run queue is FIFO, tenant fairness not preserved at this layer) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Measure ready-publication-to-runnable latency and scheduler queue contribution separately. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestScheduler, test_certification.TestFaultInjection
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 32. INV-16 async component function adapter

**Objective:** Implement and certify **INV-16 async component function adapter** so that guest-visible lowering/lifting of async function results onto this ABI.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define lowering/lifting for immediate versus subtask results and ensure generated guest stubs preserve the dual-path semantics. — **PARTIAL** (P: no generated guest stubs; deadline not mapped from the future; timeout/teardown/version-mismatch paths untested at this layer) · evidence: test_adapters.TestAsyncFunction
- [ ] Map guest language futures/promises/tasks to ABI handles without exposing raw host capability tokens where unnecessary. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Ensure guest cancellation/deadline constructs map to ABI semantics without silently weakening guarantees. — **PARTIAL** (P: no generated guest stubs; deadline not mapped from the future; timeout/teardown/version-mismatch paths untested at this layer) · evidence: test_adapters.TestAsyncFunction
- [ ] Test synchronous completion, delayed completion, trap, cancellation, timeout, teardown, and version mismatch from guest code. — **PARTIAL** (P: no generated guest stubs; deadline not mapped from the future; timeout/teardown/version-mismatch paths untested at this layer) · evidence: test_adapters.TestAsyncFunction
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestAsyncFunction
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestAsyncFunction
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestAsyncFunction
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestAsyncFunction
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestAsyncFunction
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestAsyncFunction
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestAsyncFunction
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestAsyncFunction
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 33. INV-17 streaming adapter

**Objective:** Implement and certify **INV-17 streaming adapter** so that stream item readiness, backpressure, close, error, and cancellation semantics layered on subtask readiness.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define stream-open, item-ready, item-consume, close, error, cancellation, and producer-backpressure semantics on top of subtask readiness. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Bound buffered stream items/bytes and propagate backpressure to producers instead of converting pressure into memory growth. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Specify ordering, duplicate, gap, and terminal-event rules for stream items. — **PARTIAL** (P: gap/duplicate rules unwritten; only some close/error races tested) · evidence: test_adapters.TestStream
- [ ] Test slow consumer, fast producer, cancellation mid-item, close/error races, and teardown with buffered items. — **PARTIAL** (P: gap/duplicate rules unwritten; only some close/error races tested) · evidence: test_adapters.TestStream
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestStream
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestStream
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestStream
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestStream
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestStream
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestStream
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestStream
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestStream
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 34. INV-18 completion adapter

**Objective:** Implement and certify **INV-18 completion adapter** so that one-shot completion primitive and typed result/error lifting.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define one-shot completion creation, resolve, await, take, duplicate-resolve, cancellation, and invalidation semantics. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Ensure completion payload/error type information survives lowering/lifting without ambiguous dynamic casting. — **PARTIAL** (P: type check is isinstance only; resolution races untested) · evidence: test_adapters.TestCompletion
- [ ] Reject second resolution without corrupting the first terminal value and emit diagnostic evidence. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Test resolution races and consumer abandonment with resource reclamation. — **PARTIAL** (P: type check is isinstance only; resolution races untested) · evidence: test_adapters.TestCompletion
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestCompletion
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestCompletion
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestCompletion
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestCompletion
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestCompletion
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestCompletion
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestCompletion
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestCompletion
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 35. INV-11 contract-language bindings

**Objective:** Implement and certify **INV-11 contract-language bindings** so that async annotations lowered into generated ABI stubs with version checks.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define the source-language async annotation grammar and generated ABI signatures, including version/feature requirements. — **BLOCKED** (B: INV-11 grammar belongs to INV-11; N: no diagnostics for unsupported async features)
- [ ] Make code generation deterministic and pin generator versions in build metadata. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Generate compile-time or load-time diagnostics for unsupported async features instead of silently falling back. — **NOT_DONE** (B: INV-11 grammar belongs to INV-11; N: no diagnostics for unsupported async features)
- [ ] Golden-test generated stubs and diff them in CI for contract-language changes. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_wire.TestIdl
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_wire.TestIdl
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestIdl
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_wire.TestIdl
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_wire.TestIdl
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_wire.TestIdl
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestIdl
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestIdl
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 36. INV-12 language interop bindings

**Objective:** Implement and certify **INV-12 language interop bindings** so that canonical lowering/lifting for handles, payloads, errors, cancellation, and deadlines.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define canonical mappings for handles, result unions, errors, deadlines, cancellation reasons, optional values, buffers, and resource ownership in each language. — **BLOCKED** (B: INV-12 and other languages absent; P: widths/BE/UTF-8 explicit in codec)
- [ ] Document exception/task/future mapping so language runtime behavior does not alter ABI semantics. — **BLOCKED** (B: INV-12 and other languages absent; P: widths/BE/UTF-8 explicit in codec)
- [ ] Handle integer width, endianness, UTF encoding, nullability, and lifetime differences explicitly. — **PARTIAL** (B: INV-12 and other languages absent; P: widths/BE/UTF-8 explicit in codec)
- [ ] Run cross-language round trips and negative tests using the same conformance vectors. — **BLOCKED** (B: INV-12 and other languages absent; P: widths/BE/UTF-8 explicit in codec)
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **NOT_DONE** (no executed evidence)
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **NOT_DONE** (no executed evidence)
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **NOT_DONE** (no executed evidence)
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **BLOCKED** (P: generated component dossier + SPEC, not a reviewed ADR)
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **BLOCKED** (not applicable to a component with no implementation here)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **BLOCKED** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **BLOCKED** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **BLOCKED** (P: COMPATIBILITY.md is package-level)
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **BLOCKED** (P: docs are package-level; no generated per-component reference)
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 37. INV-14 migration shim

**Objective:** Implement and certify **INV-14 migration shim** so that compatibility bridge from the previous pollable model, including deprecation telemetry and cutover rules.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Inventory every legacy pollable behavior and map it to equivalent new-ABI behavior or an explicit unsupported case. — **BLOCKED** (B: INV-14 behaviour inventory needs INV-14's source; P: deprecation counter has no workload label; no cutover deadline)
- [ ] Emit deprecation telemetry keyed to safe workload/component identifiers so remaining legacy usage can be measured before cutover. — **PARTIAL** (B: INV-14 behaviour inventory needs INV-14's source; P: deprecation counter has no workload label; no cutover deadline) · evidence: test_adapters.TestShim
- [ ] Define coexistence rules when old and new models are enabled simultaneously and prevent handle-type confusion. — **PARTIAL** (B: INV-14 behaviour inventory needs INV-14's source; P: deprecation counter has no workload label; no cutover deadline) · evidence: test_adapters.TestShim
- [ ] Provide a rollback/cutover plan with a deadline and objective removal criteria for the shim. — **PARTIAL** (B: INV-14 behaviour inventory needs INV-14's source; P: deprecation counter has no workload label; no cutover deadline) · evidence: test_adapters.TestShim
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestShim
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_adapters.TestShim
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestShim
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestShim
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestShim
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestShim
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestShim
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestShim
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 38. Cross-runtime interop harness

**Objective:** Implement and certify **Cross-runtime interop harness** so that at least two independent runtime implementations proving ABI equivalence.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Implement the same conformance suite against at least two independent runtimes, not two wrappers over one core implementation. — **BLOCKED** (B: 'two independent runtimes, not two wrappers' - there is one author and one language; the harness compares codec vs codec_alt and v4.2 model vs v4.3 host)
- [ ] Exchange serialized fixtures and live calls between runtimes where the deployment model permits cross-runtime boundaries. — **BLOCKED** (B: 'two independent runtimes, not two wrappers' - there is one author and one language; the harness compares codec vs codec_alt and v4.2 model vs v4.3 host)
- [ ] Compare not only success values but state transitions, error codes, cancellation races, timeout behavior, and malformed-input rejection. — **PARTIAL** (B: 'two independent runtimes, not two wrappers' - there is one author and one language; the harness compares codec vs codec_alt and v4.2 model vs v4.3 host) · evidence: test_wire.TestVectors
- [ ] Produce a machine-readable interop report pinned to runtime revisions and ABI version. — **PARTIAL** (B: 'two independent runtimes, not two wrappers' - there is one author and one language; the harness compares codec vs codec_alt and v4.2 model vs v4.3 host) · evidence: test_wire.TestVectors
- [ ] Define the adapter boundary as a versioned contract with explicit ownership of lowering/lifting, scheduling, suspension, wakeup, error mapping, cancellation, and resource cleanup. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_wire.TestVectors
- [ ] Guarantee that adapters do not reintroduce polling loops, blocked guest stacks, unbounded buffering, or synchronous waits on host scheduler threads. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Specify canonical error and status translation so adjacent layers cannot silently collapse timeout, cancellation, trap, host failure, unsupported-version, or invalid-handle conditions. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Provide compatibility behavior for mixed-version deployments and make unsupported combinations fail fast with actionable diagnostics before workload execution. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Validate at least one end-to-end path through every adjacent layer named by the component, including negative-path behavior and teardown. — **BLOCKED** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only)
- [ ] Measure adapter overhead independently from core ABI overhead so regressions in lowering/lifting, scheduling, or serialization can be attributed correctly. — **PARTIAL** (B: adjacent layers are absent, so no real end-to-end path; P: ownership prose thin; overhead measured for the scheduler adapter only) · evidence: test_wire.TestVectors
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestVectors
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **PARTIAL** (not applicable to a component with no implementation here) · evidence: test_wire.TestVectors
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **NOT_DONE** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestVectors
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestVectors
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# E. Security, trust, and isolation

## 39. Capability-boundary threat model

**Objective:** Implement and certify **Capability-boundary threat model** so that explicit attacker model for guest code, same-instance modules, cross-tenant callers, compromised host extensions, and forged serialized handles.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Enumerate guest, same-instance, cross-instance, cross-tenant, host-extension, operator, and serialized-boundary attacker capabilities. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Identify assets including handle authority, tenant isolation, scheduler capacity, payload confidentiality/integrity, and availability. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Create abuse cases for guessing, replay, stale-handle use, confusion between versions/types, timing probes, resource exhaustion, and malicious cancellation. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Map every threat to preventive/detective controls, test evidence, and residual risk owner. — **BLOCKED** (B: residual-risk owner unnamed)
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **NOT_DONE** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel, test_host.TestReplayTenant
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 40. Handle redaction policy

**Objective:** Implement and certify **Handle redaction policy** so that logging/tracing rules ensuring opaque tokens never appear in ordinary logs or user-visible diagnostics.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Mark handle/token fields as `secret` or equivalent in logging/telemetry schemas and enforce redaction centrally rather than at call sites. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Prevent raw handles from appearing in exceptions, repr/debug strings, crash annotations, metrics labels, traces, support bundles, or user-visible diagnostics. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Use irreversible bounded correlation IDs for debugging and document collision/rotation behavior. — **PARTIAL** (P: correlation-id collision/rotation not documented beyond per-process key) · evidence: test_security_telemetry.TestRedaction
- [ ] Add automated log-scanning tests that fail CI if known handle fixtures appear in captured output. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestRedaction
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestRedaction
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestRedaction
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestRedaction
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestRedaction
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestRedaction
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestRedaction
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestRedaction
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 41. Replay protection across serialized boundaries

**Objective:** Implement and certify **Replay protection across serialized boundaries** so that nonce/generation/instance epoch semantics if handles ever cross process or machine boundaries.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Bind serialized handles to an instance/tenant/runtime epoch and reject mismatches before lookup. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Define nonce lifetime and anti-replay storage/window semantics appropriate to whether transport is in-process, IPC, or networked. — **PARTIAL** (P: no per-transport anti-replay window; version-upgrade replay not tested) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Protect serialization integrity with authenticated transport or message authentication where the boundary is not inherently trusted. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Test capture/replay across instance restart, tenant change, slot reuse, and version upgrade. — **PARTIAL** (P: no per-transport anti-replay window; version-upgrade replay not tested) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestReplayTenant, test_wire.TestHandleEncoding, test_host.TestTeardownRestart
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 42. Tenant identity binding

**Objective:** Implement and certify **Tenant identity binding** so that host-enforced association of a handle with tenant/workload identity beyond process-local object ownership.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Associate every handle table entry with immutable tenant/workload identity established by trusted host context, not caller-supplied metadata alone. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Check identity before exposing existence/readiness state to prevent cross-tenant probing. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Carry identity across scheduler/adapters without permitting downgrade to unscoped global lookup. — **PARTIAL** (P: adapters carry views but the scheduler adapter keys by instance name; not reviewed) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Test deliberate cross-tenant handle substitution and confirm uniform rejection plus security audit evidence. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCore, test_host.TestReplayTenant, test_security_telemetry.TestAudit
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 43. Security audit events

**Objective:** Implement and certify **Security audit events** so that tamper-evident records for foreign/forged handle attempts, repeated use-after-consume, budget abuse, and cancellation anomalies.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define an append-only event schema for forged/foreign handle attempts, stale/use-after-consume, quota abuse, cancellation anomalies, and integrity failures. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Include trusted timestamp, tenant/workload correlation, host/runtime identity, event code, severity, and secret-safe object correlation. — **PARTIAL** (P: timestamp is host monotonic (not trusted), no host id; chain integrity but no access control; forensic reconstruction not exercised) · evidence: test_security_telemetry.TestAudit
- [ ] Protect event integrity at rest/export and restrict access according to security operations roles. — **PARTIAL** (P: timestamp is host monotonic (not trusted), no host id; chain integrity but no access control; forensic reconstruction not exercised) · evidence: test_security_telemetry.TestAudit
- [ ] Test alert generation and forensic reconstruction from synthetic attack sequences. — **PARTIAL** (P: timestamp is host monotonic (not trusted), no host id; chain integrity but no access control; forensic reconstruction not exercised) · evidence: test_security_telemetry.TestAudit
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestAudit
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestAudit
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestAudit
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestAudit
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestAudit
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestAudit
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestAudit
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestAudit
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 44. Resource-exhaustion adversarial suite

**Objective:** Implement and certify **Resource-exhaustion adversarial suite** so that handle spray, wait-set abuse, cancellation storms, completion storms, reason-cardinality abuse, and tombstone churn.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Build adversarial scenarios for handle spray, maximum wait sets, cancellation storms, completion storms, tombstone churn, reason-code abuse, and rapid instance creation/destruction. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Measure CPU, memory, lock contention, queue growth, scheduler latency, refusal behavior, and recovery time under each attack. — **PARTIAL** (P: CPU/lock contention not measured; recovery phases short) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Verify hard quotas engage before process instability and that one tenant cannot force global resource collapse within declared isolation goals. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Include mixed attacks and long-running recovery phases to detect deferred leaks or starvation. — **PARTIAL** (P: CPU/lock contention not measured; recovery phases short) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness, test_host.TestSubscribe
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 45. Side-channel review

**Objective:** Implement and certify **Side-channel review** so that timing/error-message analysis for cross-tenant existence probing and readiness leakage.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Compare response codes, message size, processing time, cache behavior, and wakeup timing for valid, invalid, foreign, stale, and unknown handles. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Define what readiness/existence information is intentionally observable and eliminate accidental distinctions beyond that contract. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Use statistical timing tests where cross-tenant timing is in scope and record environment noise assumptions. — **PARTIAL** (P: timing compared by median over 400 samples with a coarse 5x bound, noise not modelled; explain/metrics surface not reviewed) · evidence: test_security_telemetry.TestSideChannel
- [ ] Review metrics/debug endpoints for indirect side channels that bypass the primary API. — **PARTIAL** (P: timing compared by median over 400 samples with a coarse 5x bound, noise not modelled; explain/metrics surface not reviewed) · evidence: test_security_telemetry.TestSideChannel
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestSideChannel
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_security_telemetry.TestSideChannel
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestSideChannel
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestSideChannel
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestSideChannel
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestSideChannel
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestSideChannel
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestSideChannel
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 46. Supply-chain attestation

**Objective:** Implement and certify **Supply-chain attestation** so that signed release artifact, provenance statement, dependency lock, and SBOM for the production implementation.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Generate an SBOM in a standard format, pin dependencies/toolchains, and record source and build provenance for every release. — **PARTIAL** (B: no signing key/signer; N: no vulnerability scan; P: SBOM is empty because there are zero dependencies) · evidence: test_ops.TestRelease
- [ ] Sign artifacts and provenance with managed keys; document rotation, revocation, compromise response, and verification instructions. — **BLOCKED** (B: no signing key/signer; N: no vulnerability scan; P: SBOM is empty because there are zero dependencies)
- [ ] Verify dependency hashes/licenses and fail builds on unapproved mutable or unpinned sources. — **PARTIAL** (B: no signing key/signer; N: no vulnerability scan; P: SBOM is empty because there are zero dependencies) · evidence: test_ops.TestRelease
- [ ] Attach vulnerability scan results and reproducibility evidence to the release record. — **NOT_DONE** (B: no signing key/signer; N: no vulnerability scan; P: SBOM is empty because there are zero dependencies)
- [ ] Create a written threat model with assets, trust boundaries, attacker capabilities, abuse cases, security invariants, and explicit non-goals; review it whenever serialization or cross-tenant scope changes. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Treat opaque handles, correlation identifiers, and tenant/workload bindings as security-sensitive capability material; define where they may exist in memory, logs, traces, dumps, and diagnostics. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Design failure responses to avoid existence or readiness oracles across tenant boundaries; normalize error shape/timing where practical and document residual leakage. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Rate-limit and account security-relevant invalid operations such as forged handles, replay, use-after-consume, cancellation storms, and oversized wait sets. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_ops.TestRelease
- [ ] Generate tamper-evident, access-controlled audit evidence for security-significant events and define retention, integrity verification, clock source, and incident export procedures. — **PARTIAL** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review) · evidence: test_ops.TestRelease
- [ ] Require independent security review before release and track all findings to remediation, accepted risk with owner/expiry, or verified false positive. — **BLOCKED** (P: invalid operations are accounted and audited but not rate-limited; audit chain has no access control; B: independent security review)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestRelease
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_ops.TestRelease
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# F. Observability and SLO instrumentation

## 47. Metrics exporter

**Objective:** Implement and certify **Metrics exporter** so that production counters/gauges/histograms for open subtasks, ready subtasks, refusals, cancellations, abandoned results, wakeup latency, wait size, and host-table memory.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define counters for allocations/completions/takes/cancels/refusals/errors, gauges for live/ready/waiters/memory, and histograms for wait/wakeup/operation latency. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify labels that permit instance/workload/tenant analysis without unbounded IDs or secret material. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Reconcile counters against lifecycle invariants—for example terminal outcomes plus live entries must explain total admitted work within documented exceptions. — **PARTIAL** (P: table invariants reconciled, counters not; N: exporter overhead not load-tested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Load-test exporter overhead and set a maximum acceptable CPU/memory cost. — **NOT_DONE** (P: table invariants reconciled, counters not; N: exporter overhead not load-tested)
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestTelemetry
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 48. Cancellation latency histogram

**Objective:** Implement and certify **Cancellation latency histogram** so that scheduler-tick or wall-clock measurement needed to verify the declared p99 cancellation SLO.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Timestamp cancellation request and acknowledgment/terminal transition using a monotonic clock and define exactly which interval the histogram measures. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Use bucket boundaries that resolve the declared p50/p95/p99 SLO rather than generic defaults. — **NOT_DONE** (N: buckets are generic log2, not derived from an SLO; P: alert rule written, not verified with injected delay)
- [ ] Segment only by bounded dimensions such as outcome or workload class; do not label by raw handle or user-controlled reason text. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Create an alert on sustained SLO breach and verify it against controlled injected delays. — **PARTIAL** (N: buckets are generic log2, not derived from an SLO; P: alert rule written, not verified with injected delay) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestCancellation, test_security_telemetry.TestTelemetry
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 49. Readiness-to-resume latency histogram

**Objective:** Implement and certify **Readiness-to-resume latency histogram** so that host-ready timestamp through scheduler resume, with p50/p95/p99/worst-case reporting.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Record host readiness publication, scheduler enqueue, scheduler dispatch, and guest resume timestamps so latency can be decomposed. — **PARTIAL** (P: publication, runnable and resume stamped; guest resume is outside this model; N: batching/coalescing treatment unwritten) · evidence: test_adapters.TestScheduler
- [ ] Define treatment of batching, coalescing, paused instances, priority classes, and scheduler overload in the metric. — **NOT_DONE** (P: publication, runnable and resume stamped; guest resume is outside this model; N: batching/coalescing treatment unwritten)
- [ ] Measure p50/p95/p99/max and publish both absolute SLO and regression budget. — **PARTIAL** (P: publication, runnable and resume stamped; guest resume is outside this model; N: batching/coalescing treatment unwritten) · evidence: test_adapters.TestScheduler
- [ ] Correlate stuck-ready gauges with latency histograms to distinguish lost wakeup from simple scheduler backlog. — **PARTIAL** (P: publication, runnable and resume stamped; guest resume is outside this model; N: batching/coalescing treatment unwritten) · evidence: test_adapters.TestScheduler
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_adapters.TestScheduler
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_adapters.TestScheduler
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestScheduler
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestScheduler
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestScheduler
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestScheduler
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestScheduler
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestScheduler
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 50. Structured event log schema

**Objective:** Implement and certify **Structured event log schema** so that stable instance/tenant/workload/operation IDs with secret-safe handle correlation identifiers.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Version the event schema and define required fields for runtime, instance, tenant/workload, operation, lifecycle state, outcome, error code, and correlation ID. — **PARTIAL** (P: schema fixed but not version-tagged) · evidence: test_security_telemetry.TestTelemetry
- [ ] Classify fields by sensitivity and forbid raw payloads/handles by default. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Guarantee stable machine-parseable values; human messages are supplemental and must not be used for automation. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Provide schema validation in CI and compatibility tests for event consumers. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestTelemetry
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 51. Distributed trace propagation

**Objective:** Implement and certify **Distributed trace propagation** so that trace context across call creation, async suspension, readiness publication, and resumption.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Propagate trace context across call creation, suspension, readiness publication, scheduler wake, and resumed execution without keeping spans artificially active on blocked threads. — **PARTIAL** (N: no span/link model for fan-out/retries; P: scheduler wake not traced) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define span/link model for fan-out, fan-in, retries, detached children, and cross-runtime boundaries. — **NOT_DONE** (N: no span/link model for fan-out/retries; P: scheduler wake not traced)
- [ ] Sanitize baggage and prohibit handle tokens or untrusted high-cardinality payload data. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Test trace continuity through cancellation, timeout, trap, and sampled/unsampled boundaries. — **PARTIAL** (N: no span/link model for fan-out/retries; P: scheduler wake not traced) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestTelemetry
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 52. Explain/debug endpoint

**Objective:** Implement and certify **Explain/debug endpoint** so that bounded operator view of live counts, states, budgets, refusal causes, and dependency health without exposing handle tokens or payloads.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Expose only bounded aggregate state: counts, age distributions, budget utilization, refusal causes, dependency health, and safe correlation identifiers. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Require authentication/authorization and audit access; do not expose raw payloads, handle tokens, tenant secrets, or unrestricted per-handle lookup. — **BLOCKED** (B: there is no endpoint server to authenticate; N: explain() under overload not tested)
- [ ] Set response size/time limits and paginate or aggregate large views so debugging cannot exhaust the runtime. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Test the endpoint while the system is overloaded and ensure failure of the endpoint cannot block core ABI progress. — **NOT_DONE** (B: there is no endpoint server to authenticate; N: explain() under overload not tested)
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestTelemetry
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 53. Dashboard and alert pack

**Objective:** Implement and certify **Dashboard and alert pack** so that saturation, stuck-ready, cancellation-latency, refusal-rate, unexpected foreign-handle, and wakeup-loss indicators.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Create panels for admission/refusal, live/ready state, oldest age, memory/table saturation, cancellation latency, readiness-to-resume latency, foreign-handle events, and lost-wakeup indicators. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Define alert thresholds from SLOs/invariants with severity, minimum duration, anti-flap behavior, and owner. — **PARTIAL** (B: never imported into Grafana/Prometheus or exercised in staging; P: thresholds PROPOSED, no owner) · evidence: test_ops.TestRelease
- [ ] Link each alert directly to a tested runbook and the exact diagnostic queries needed for first response. — **PARTIAL** (B: never imported into Grafana/Prometheus or exercised in staging; P: thresholds PROPOSED, no owner) · evidence: test_ops.TestRelease
- [ ] Exercise alerts in staging through synthetic faults and record expected versus observed notification latency. — **BLOCKED** (B: never imported into Grafana/Prometheus or exercised in staging; P: thresholds PROPOSED, no owner)
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_ops.TestRelease
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_ops.TestRelease
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestRelease
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_ops.TestRelease
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 54. Telemetry retention/sampling policy

**Objective:** Implement and certify **Telemetry retention/sampling policy** so that high-cardinality controls and privacy-safe export behavior.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Classify telemetry by operational value and sensitivity, then set retention, aggregation, and deletion periods per class. — **PARTIAL** (N: no collector-outage behaviour; B: privacy review) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define tail/head sampling and high-cardinality suppression that preserve incident usefulness without unbounded cost. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify export behavior during collector outage, including bounded local buffering and drop accounting. — **NOT_DONE** (N: no collector-outage behaviour; B: privacy review)
- [ ] Document privacy/security review, access controls, and deletion obligations for tenant/workload identifiers. — **BLOCKED** (N: no collector-outage behaviour; B: privacy review)
- [ ] Define each metric/event/trace field with unit, type, cardinality budget, labels/attributes, aggregation semantics, reset behavior, and owner. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Use secret-safe correlation identifiers instead of raw opaque handles; correlation must support debugging while preventing handle reconstruction or replay. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Record monotonic timestamps at state transitions needed for latency SLOs and preserve enough context to separate host, scheduler, queueing, and guest execution latency. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Establish cardinality controls, sampling rules, and backpressure behavior so telemetry cannot become the cause of ABI overload or unbounded memory growth. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Provide dashboards and alerts tied to explicit SLOs or invariants, with runbook links and tested alert-routing ownership. — **PARTIAL** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested) · evidence: test_security_telemetry.TestTelemetry
- [ ] Test telemetry under overload, partial exporter failure, exporter backpressure, and disabled-observability modes; core ABI progress must not depend on telemetry availability. — **NOT_DONE** (P: no per-metric unit/cardinality sheet; alert ownership unassigned; N: exporter failure/backpressure untested)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_security_telemetry.TestTelemetry
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_security_telemetry.TestTelemetry
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_security_telemetry.TestTelemetry
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_security_telemetry.TestTelemetry
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# G. Verification and performance certification

## 55. Property-based state-machine tests

**Objective:** Implement and certify **Property-based state-machine tests** so that randomized legal/illegal operation sequences validating lifecycle invariants.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Model the lifecycle as a generator of legal and illegal operation sequences with explicit state invariants. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Generate actions including allocate, complete, wait, take, cancel, cancel-all, abandon, timeout, teardown, and invalid-handle operations. — **PARTIAL** (P: teardown not in the generator; N: no shrinking) · evidence: test_certification.TestProperty
- [ ] Shrink failing traces to minimal reproducible sequences and persist seeds/regressions in the corpus. — **NOT_DONE** (P: teardown not in the generator; N: no shrinking)
- [ ] Assert no double completion/consume, no terminal resurrection, correct accounting, and eventual reclamation after every generated trace. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestProperty
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestProperty
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestProperty
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestProperty
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestProperty
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestProperty
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestProperty
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 56. Protocol/handle fuzzing

**Objective:** Implement and certify **Protocol/handle fuzzing** so that malformed encodings, truncated handles, invalid versions, oversized sets, and random failure envelopes.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Fuzz binary/text protocol decoders with truncation, extension, bit flips, length corruption, unknown versions, invalid discriminants, and oversized collections. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Seed the corpus with every official conformance vector plus previously discovered crashers. — **PARTIAL** (B: sanitizers; P: seeds are generator outputs not the full vector corpus; mutations are byte-level) · evidence: test_certification.TestFuzz
- [ ] Run with sanitizers/instrumentation and treat hangs, unbounded allocation, assertion-only safety, or differential decoder behavior as failures. — **BLOCKED** (B: sanitizers; P: seeds are generator outputs not the full vector corpus; mutations are byte-level)
- [ ] Add structure-aware mutations for handle fields, version bits, lengths, and error envelopes. — **PARTIAL** (B: sanitizers; P: seeds are generator outputs not the full vector corpus; mutations are byte-level) · evidence: test_certification.TestFuzz
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestFuzz
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestFuzz
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestFuzz
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestFuzz
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestFuzz
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestFuzz
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestFuzz
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 57. Concurrency race suite

**Objective:** Implement and certify **Concurrency race suite** so that complete/wait/take/cancel/cancel-all/teardown interleavings under high thread/task counts.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Exercise complete/wait/take/cancel/cancel-all/teardown from many threads/tasks with randomized yields and forced scheduler interleavings. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Target ABA/slot-reuse, duplicate publication, waiter removal, budget reservation/release, and late-completion races. — **PARTIAL** (B: thread sanitizer; P: slot reuse covered in TestGenerations not under threads; iteration gate small) · evidence: test_certification.TestRaces
- [ ] Run under race detector/thread sanitizer or equivalent where the production language supports it. — **BLOCKED** (B: thread sanitizer; P: slot reuse covered in TestGenerations not under threads; iteration gate small)
- [ ] Require zero data races and zero invariant violations over a defined high-iteration gate, persisting failing seeds/traces. — **PARTIAL** (B: thread sanitizer; P: slot reuse covered in TestGenerations not under threads; iteration gate small) · evidence: test_certification.TestRaces
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestRaces
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestRaces
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestRaces
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestRaces
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestRaces
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestRaces
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestRaces
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 58. Lost-wakeup stress test

**Objective:** Implement and certify **Lost-wakeup stress test** so that millions of readiness/subscription races proving no indefinite stall.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Construct the exact subscribe-versus-publish race and run it across multiple cores for millions of iterations. — **PARTIAL** (P: 3,000 x SCALE iterations on one host, not millions across cores; removal-vs-publication not included) · evidence: test_certification.TestLostWakeup
- [ ] Include publication before registration, between check/register, during cancellation/removal, and immediately after teardown. — **PARTIAL** (P: 3,000 x SCALE iterations on one host, not millions across cores; removal-vs-publication not included) · evidence: test_certification.TestLostWakeup
- [ ] Fail on any waiter exceeding a strict bounded completion time once readiness has been published. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Record CPU topology/runtime version so regressions tied to architecture or scheduler can be reproduced. — **PARTIAL** (P: 3,000 x SCALE iterations on one host, not millions across cores; removal-vs-publication not included) · evidence: test_certification.TestLostWakeup
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestLostWakeup
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestLostWakeup
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestLostWakeup
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestLostWakeup
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestLostWakeup
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestLostWakeup
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestLostWakeup
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 59. Soak and churn test

**Objective:** Implement and certify **Soak and churn test** so that long-duration create/complete/cancel cycles proving bounded memory and tombstone behavior.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Run sustained create/complete/cancel/timeout/abandon cycles long enough to cross allocator and tombstone aging boundaries. — **PARTIAL** (P: 20,000 x SCALE cycles in seconds, not long-duration; patterns mixed randomly, not rotated in phases) · evidence: test_certification.TestSoakOverload
- [ ] Track RSS/heap, table bytes, tombstones, queue depth, live counters, allocator fragmentation, and latency drift over time. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Define acceptable steady-state memory envelope and require memory to return near baseline after a drain period. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Rotate workload patterns during the soak to expose phase-dependent leaks and stale accounting. — **PARTIAL** (P: 20,000 x SCALE cycles in seconds, not long-duration; patterns mixed randomly, not rotated in phases) · evidence: test_certification.TestSoakOverload
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestSoakOverload
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestSoakOverload
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestSoakOverload
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestSoakOverload
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestSoakOverload
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestSoakOverload
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestSoakOverload
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 60. Overload test

**Objective:** Implement and certify **Overload test** so that sustained budget exhaustion and recovery with fairness and tail-latency measurements.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Drive every budget scope into refusal while mixing high/low priority tenants and verify deterministic refusal codes. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Measure tail latency, fairness/starvation, CPU, memory, queue depth, and recovery after load returns below capacity. — **PARTIAL** (P: p99 recorded, CPU not; fail-fast cost not profiled) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Prove overload control fails fast without expensive allocation or global contention amplification. — **PARTIAL** (P: p99 recorded, CPU not; fail-fast cost not profiled) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Verify no permanent capacity loss after refused/admitted/cancelled work is reclaimed. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestSoakOverload, test_host.TestBudgetsFairness
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 61. Benchmark suite

**Objective:** Implement and certify **Benchmark suite** so that call allocation, completion publication, wait, take, cancel, and teardown latency/throughput baselines.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Benchmark allocation, completion publication, wait registration/wakeup, take, cancel, batch delivery, teardown, and invalid-handle rejection separately. — **PARTIAL** (P: core ops benchmarked at 1 and 8 threads, no wait-registration benchmark; environment recorded, no warmup rule; N: no CI regression gate) · evidence: test_ops.TestBench
- [ ] Report throughput and latency distributions across concurrency levels rather than only averages. — **PARTIAL** (P: core ops benchmarked at 1 and 8 threads, no wait-registration benchmark; environment recorded, no warmup rule; N: no CI regression gate) · evidence: test_ops.TestBench
- [ ] Use fixed machine profiles, pinned toolchain/runtime versions, warmup rules, sample counts, and statistical regression thresholds. — **PARTIAL** (P: core ops benchmarked at 1 and 8 threads, no wait-registration benchmark; environment recorded, no warmup rule; N: no CI regression gate) · evidence: test_ops.TestBench
- [ ] Store baselines by architecture/runtime and fail CI/release gates on significant unexplained regression. — **NOT_DONE** (P: core ops benchmarked at 1 and 8 threads, no wait-registration benchmark; environment recorded, no warmup rule; N: no CI regression gate)
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_ops.TestBench
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestBench
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestBench
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (downgraded: evidence tests missing or failing)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestBench
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestBench
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 62. Architecture compatibility matrix

**Objective:** Implement and certify **Architecture compatibility matrix** so that supported CPU architectures, OS/runtime versions, host runtimes, and ABI versions.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Enumerate supported CPU architectures, OS versions, runtime versions, ABI versions, compiler/toolchain versions, endianness, pointer width, and relevant security modes. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Classify each combination as required, best-effort, deprecated, or unsupported with test depth and owner. — **PARTIAL** (B: other OS/arch/runtimes not available; N: install-time blocking of unsupported rows) · evidence: test_ops.TestRelease
- [ ] Run at least smoke/conformance tests on every supported row and full stress/certification on designated release-critical rows. — **BLOCKED** (B: other OS/arch/runtimes not available; N: install-time blocking of unsupported rows)
- [ ] Publish compatibility changes as versioned release metadata and block installation/startup on explicitly unsupported combinations where practical. — **NOT_DONE** (B: other OS/arch/runtimes not available; N: install-time blocking of unsupported rows)
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_ops.TestRelease
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **NOT_DONE** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 63. Fault-injection suite

**Objective:** Implement and certify **Fault-injection suite** so that callee trap, host crash, scheduler stall, clock failure, RNG failure, teardown race, and dependency loss.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Inject callee trap, host crash, scheduler stall, monotonic-clock anomaly, RNG failure, allocator pressure, teardown race, exporter failure, and dependency loss. — **PARTIAL** (P: trap, clock, RNG, scheduler stall, producer death, callback faults injected; host crash only as restart(); allocator pressure only via memory ceilings) · evidence: test_certification.TestFaultInjection
- [ ] Define expected error/state/accounting outcome for every injected fault before running the test. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Verify forward progress and bounded recovery after transient faults and deterministic fail-closed behavior for security-critical dependency failure. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Preserve reproducible fault schedules/seeds and include them in release certification. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_certification.TestFaultInjection
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_certification.TestFaultInjection
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_certification.TestFaultInjection
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_certification.TestFaultInjection
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_certification.TestFaultInjection
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_certification.TestFaultInjection
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_certification.TestFaultInjection
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 64. Independent implementation conformance test

**Objective:** Implement and certify **Independent implementation conformance test** so that same vectors executed against the reference model and each production runtime.

**Priority:** P0  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Run identical conformance vectors and state-machine scenarios against the reference model and each independent production implementation. — **BLOCKED** (B: no independent production implementation exists; results unsigned)
- [ ] Compare encoded bytes, return values, error codes, legal/illegal transitions, cancellation/timeout race outcomes, and resource reclamation. — **PARTIAL** (B: no independent production implementation exists; results unsigned) · evidence: test_wire.TestVectors
- [ ] Treat undocumented behavioral divergence as a release blocker even when both implementations appear locally reasonable. — **BLOCKED** (B: no independent production implementation exists; results unsigned)
- [ ] Publish signed machine-readable conformance results tied to exact implementation revisions. — **BLOCKED** (B: no independent production implementation exists; results unsigned)
- [ ] Make tests deterministic and reproducible by recording random seeds, runtime/OS/CPU metadata, ABI version, feature flags, and relevant scheduler configuration. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Run correctness tests in debug and optimized/release builds so safety does not rely on assertions or debug-only checks. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Define pass/fail thresholds before execution, including iteration counts, duration, allowable error rate, latency regression budget, memory-growth bound, and flake policy. — **PARTIAL** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows) · evidence: test_wire.TestVectors
- [ ] Capture machine-readable artifacts for every test run: logs, metrics, seeds/corpus, benchmark distributions, crash dumps where applicable, and environment manifest. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Exercise both legal and illegal protocol sequences and verify not only returned errors but also post-error state, memory reclamation, and subsequent forward progress. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Run the certification suite against the reference implementation and every supported production runtime/architecture combination before release promotion. — **BLOCKED** (P: iteration thresholds set by SCALE, not approved; B: no production runtime/architecture rows)
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_wire.TestVectors
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_wire.TestVectors
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **PARTIAL** (not applicable to a component with no implementation here) · evidence: test_wire.TestVectors
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **NOT_DONE** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_wire.TestVectors
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_wire.TestVectors
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# H. Release, packaging, and operations

## 65. Package/build metadata

**Objective:** Implement and certify **Package/build metadata** so that explicit Python/runtime compatibility and dependency metadata for this reference package or its production equivalent.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Declare package name/version, language/runtime requirement, supported architectures, optional features, dependencies, license, entry points, and build backend explicitly. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Pin or constrain dependencies reproducibly and produce lockfiles/manifests appropriate to the implementation language. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Embed ABI/protocol version and build revision in runtime introspection without changing wire compatibility accidentally. — **PARTIAL** (P: no build revision embedded; clean isolated install not run) · evidence: test_ops.TestRelease
- [ ] Validate clean install/build/test from an isolated environment with no undeclared developer-machine dependencies. — **PARTIAL** (P: no build revision embedded; clean isolated install not run) · evidence: test_ops.TestRelease
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestRelease
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_ops.TestRelease
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 66. CI pipeline

**Objective:** Implement and certify **CI pipeline** so that compile, unit, optimized-mode, fuzz, race, benchmark-regression, SBOM, signing, and gate stages.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Create gated stages for format/lint, compile/type-check, unit, optimized/release mode, property, fuzz smoke, race, conformance, benchmark regression, SBOM, signing, packaging, and provenance. — **PARTIAL** (P: ci.sh has no lint/type-check stage; N: no cache exists; B: protected-branch approvals) · evidence: test_ops.TestRelease
- [ ] Cache only artifacts whose cache keys include all correctness-relevant compiler/dependency/configuration inputs. — **NOT_DONE** (P: ci.sh has no lint/type-check stage; N: no cache exists; B: protected-branch approvals)
- [ ] Require protected-branch/release approvals and prevent unsigned or untested artifacts from bypassing the pipeline. — **BLOCKED** (P: ci.sh has no lint/type-check stage; N: no cache exists; B: protected-branch approvals)
- [ ] Publish machine-readable test and security artifacts with retention sufficient for release audit. — **PARTIAL** (P: ci.sh has no lint/type-check stage; N: no cache exists; B: protected-branch approvals) · evidence: test_ops.TestRelease
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestRelease
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_ops.TestRelease
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 67. Version compatibility matrix

**Objective:** Implement and certify **Version compatibility matrix** so that supported combinations of INV-11/12/14/16/17/18 and SCH-01 interface versions.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] List supported combinations of INV-11/12/14/16/17/18, SCH-01, host runtime, and INV-15 ABI versions. — **BLOCKED** (B: adjacent component versions are unknown here; E: fail-fast on unsupported major)
- [ ] Mark combinations as fully supported, transitional, test-only, deprecated, or blocked and define the enforcement point. — **PARTIAL** (B: adjacent component versions are unknown here; E: fail-fast on unsupported major) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Generate pairwise/full-matrix tests for high-risk boundaries and fail fast before workload start on blocked combinations. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Version the matrix with releases and document upgrade ordering for rolling deployments. — **PARTIAL** (B: adjacent component versions are unknown here; E: fail-fast on unsupported major) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_adapters.TestScheduler, test_wire.TestNegotiation
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 68. Canary rollout procedure

**Objective:** Implement and certify **Canary rollout procedure** so that staged enablement with measurable abort thresholds tied to refusals, stalls, latency, and errors.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define staged percentages/cohorts, minimum observation windows, health metrics, and explicit abort thresholds before rollout begins. — **EVIDENCED** · evidence: test_ops.TestRollbackHook
- [ ] Canary representative workload types and architectures, not only low-risk synthetic traffic. — **BLOCKED** (B: representative workloads/architectures; P: hook compares a subset of signals, pause is not automated)
- [ ] Compare refusal, error, cancellation, stuck-ready, wakeup latency, scheduler latency, memory, and CPU to a control cohort. — **PARTIAL** (B: representative workloads/architectures; P: hook compares a subset of signals, pause is not automated) · evidence: test_ops.TestRollbackHook
- [ ] Automate pause/rollback when hard abort criteria are met and retain evidence for rollout review. — **PARTIAL** (B: representative workloads/architectures; P: hook compares a subset of signals, pause is not automated) · evidence: test_ops.TestRollbackHook
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRollbackHook
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_ops.TestRollbackHook
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_ops.TestRollbackHook
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_ops.TestRollbackHook
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_ops.TestRollbackHook
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_ops.TestRollbackHook
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestRollbackHook
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_ops.TestRollbackHook
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRollbackHook
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestRollbackHook
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 69. Automated rollback hook

**Objective:** Implement and certify **Automated rollback hook** so that restore prior runtime/ABI implementation and invalidate incompatible live handles safely.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Define the exact artifact/configuration rollback unit and verify old runtime/ABI compatibility with persisted or live state. — **PARTIAL** (B: no deployment system to automate restore or exercise) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Invalidate or drain incompatible live handles safely before switching implementations; never reinterpret new-format handles under old code. — **EVIDENCED** · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Automate restoration of binaries/config/feature flags and verify health checks plus conformance smoke after rollback. — **BLOCKED** (B: no deployment system to automate restore or exercise)
- [ ] Exercise rollback from partially deployed and failure-mid-rollout states on a recurring schedule. — **BLOCKED** (B: no deployment system to automate restore or exercise)
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_ops.TestRollbackHook, test_host.TestTeardownRestart
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 70. Emergency disable/drain control

**Objective:** Implement and certify **Emergency disable/drain control** so that operator mechanism to stop admission, drain/cancel live subtasks, and preserve diagnostics.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Provide authenticated operator controls to stop new admission at instance/workload/tenant/global scopes as appropriate. — **PARTIAL** (P: instance + global scope only, unauthenticated, no grace deadline; B: control-plane loss) · evidence: test_host.TestDrainDisable
- [ ] Support policy-selected drain, cancel, or forced invalidation with grace deadlines and clear progress reporting. — **PARTIAL** (P: instance + global scope only, unauthenticated, no grace deadline; B: control-plane loss) · evidence: test_host.TestDrainDisable
- [ ] Preserve diagnostics and security/audit evidence while preventing the control itself from leaking secret handle/payload data. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Test control-plane loss and ensure an initiated emergency action has deterministic behavior if the operator connection disappears. — **BLOCKED** (P: instance + global scope only, unauthenticated, no grace deadline; B: control-plane loss)
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_host.TestDrainDisable
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_host.TestDrainDisable
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_host.TestDrainDisable
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_host.TestDrainDisable
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_host.TestDrainDisable
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **EVIDENCED** · evidence: test_host.TestDrainDisable
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **PARTIAL** (P: adversarial coverage uneven across components) · evidence: test_host.TestDrainDisable
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **PARTIAL** (P: baselines for core ops only; no approved budget) · evidence: test_host.TestDrainDisable
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_host.TestDrainDisable
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **PARTIAL** (P: docs are package-level; no generated per-component reference) · evidence: test_host.TestDrainDisable
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 71. Incident runbook

**Objective:** Implement and certify **Incident runbook** so that lost wakeup, runaway subtasks, cancellation failure, handle-forgery alarms, and scheduler integration failure.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Write step-by-step diagnosis and containment for lost wakeup, runaway subtasks, cancellation failure, forged-handle alarms, table saturation, scheduler integration failure, and restart loops. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Include exact dashboards/queries, safe data to collect, decision points, escalation contacts/roles, and rollback/drain commands. — **PARTIAL** (B: escalation contacts and exercises need people) · evidence: test_ops.TestRelease
- [ ] Define severity criteria, customer/tenant impact assessment, evidence preservation, and post-incident review requirements. — **BLOCKED** (B: escalation contacts and exercises need people)
- [ ] Tabletop and live-fire exercise the runbook and update it from observed gaps. — **BLOCKED** (B: escalation contacts and exercises need people)
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **NOT_DONE** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

## 72. Patch/vulnerability/EOL policy

**Objective:** Implement and certify **Patch/vulnerability/EOL policy** so that ownership, severity SLA, supported release window, deprecation schedule, and migration obligations.

**Priority:** P1  
**Owner:** _TBD_  
**Reviewers:** _ABI / Runtime / Security / SRE as applicable_  
**Evidence links:** _Design / code / tests / benchmarks / dashboards / release artifact_


### Technical checklist
- [ ] Assign vulnerability intake/triage/patch owners, severity methodology, response SLA, embargo/coordinated-disclosure process, and release channels. — **BLOCKED** (B: owners; N: exception tracking)
- [ ] Define supported major/minor release windows, security-fix backport policy, deprecation notice period, and hard EOL date semantics. — **PARTIAL** (B: owners; N: exception tracking) · evidence: test_ops.TestRelease
- [ ] Publish migration obligations for removed/changed ABI features and identify who owns compatibility tooling/documentation. — **PARTIAL** (B: owners; N: exception tracking) · evidence: test_ops.TestRelease
- [ ] Track exceptions with explicit expiry and prevent unsupported/EOL versions from silently receiving indefinite best-effort support. — **NOT_DONE** (B: owners; N: exception tracking)
- [ ] Make build and release outputs reproducible or explain unavoidable nondeterminism; pin toolchains and dependencies and record the complete build environment. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Define signed provenance for source revision, generated bindings, dependencies, compiler/toolchain versions, test evidence, SBOM, and final artifact digest. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Automate compatibility and rollback checks in CI/CD rather than relying on operator memory; unsupported combinations must be blocked before rollout. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Treat drain, rollback, emergency disable, and incident response as tested product features with recurring exercises and measurable recovery objectives. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Assign an owner and backup owner for every operational control, alert, runbook, vulnerability SLA, and end-of-life decision. — **BLOCKED** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners)
- [ ] Retain release evidence sufficient to reconstruct why an artifact was promoted, including approvals, exceptions, risk acceptances, and exact artifact hashes. — **PARTIAL** (P: archive timestamps not normalised; no recurring exercises; B: signing and owners) · evidence: test_ops.TestRelease
- [ ] Create an ADR/design note that states the component purpose, scope, non-goals, dependencies, trust boundary, public API surface, and interaction with the INV-15 lifecycle. — **PARTIAL** (P: generated component dossier + SPEC, not a reviewed ADR) · evidence: test_ops.TestRelease
- [ ] Define explicit preconditions, postconditions, invariants, and forbidden states; encode machine-checkable invariants as assertions/tests in non-production and release-safe validation where required. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Enumerate failure modes and map each to a stable machine-readable result; prohibit ambiguous sentinel values and free-form error parsing. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Specify resource ownership and cleanup for success, error, cancellation, timeout, caller abandonment, instance teardown, and host termination. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add structured observability sufficient to answer: what operation occurred, for which instance/workload, at what lifecycle state, why it failed/refused, and how long the transition took. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add unit tests for nominal, boundary, empty, maximum-size, duplicate, invalid, stale, repeated, and already-completed/already-consumed cases relevant to the component. — **NOT_DONE** (not applicable to a component with no implementation here)
- [ ] Add adversarial tests for malformed input, quota exhaustion, race conditions, repeated retries, cancellation storms, teardown races, and dependency failure. — **NOT_DONE** (P: adversarial coverage uneven across components)
- [ ] Define performance budgets and record a baseline for latency, throughput, allocation rate, memory footprint, and tail behavior under representative concurrency. — **NOT_DONE** (P: baselines for core ops only; no approved budget)
- [ ] Document compatibility requirements, feature/version gates, migration implications, rollback behavior, and the exact condition under which older/newer peers are rejected. — **PARTIAL** (P: COMPATIBILITY.md is package-level) · evidence: test_ops.TestRelease
- [ ] Document operator/developer usage, examples, error reference, debugging steps, metrics, alerts, and known limitations; generated documentation must match the shipped version. — **EVIDENCED** · evidence: test_ops.TestRelease
- [ ] Require code review plus test evidence and security review proportional to risk; unresolved P0/P1 findings block release unless an explicit time-bounded risk acceptance is recorded. — **BLOCKED** (B: code/security review requires reviewers)
- [ ] Close the component only when implementation, tests, documentation, telemetry, compatibility evidence, and release artifacts are linked from the tracking item and independently reproducible. — **BLOCKED** (B: closure requires owner, reviewer and release artifacts)

### Acceptance record
- **Implementation revision:** _TBD_
- **Test/certification artifact:** _TBD_
- **Performance evidence:** _TBD_
- **Security review:** _TBD / N/A with rationale_
- **Operational documentation:** _TBD_
- **Final status:** _OPEN / BLOCKED / VERIFIED_

# Recommended execution sequence

1. Components **1–8**: freeze the wire/IDL contract and conformance corpus.
2. Components **9–18**: close deadline, timeout, cancellation, retry, budget, fairness, and drain semantics.
3. Components **19–30**: implement the production waitable table, wakeup path, publication, invalidation, accounting, and ownership model.
4. Components **31–38**: integrate scheduler, adjacent INV layers, migration, and cross-runtime interoperability.
5. Components **39–54**: close security/isolation and production observability/SLO instrumentation.
6. Components **55–64**: run certification, stress, fuzz, race, performance, compatibility, and fault-injection gates.
7. Components **65–72**: finalize packaging, CI, compatibility policy, rollout, rollback, emergency control, runbooks, and lifecycle governance.

# Completion metrics

- Components: **72**
- Component-level checklist items: **1,584**
- Global Definition-of-Done items: **15**
- Total checkboxes: **1,599**

