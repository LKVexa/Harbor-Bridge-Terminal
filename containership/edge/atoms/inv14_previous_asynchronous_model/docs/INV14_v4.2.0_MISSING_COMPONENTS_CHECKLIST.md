# INV-14 v4.2.0 — Missing Components Professional Engineering Checklist

**Element:** INV-14 — Previous asynchronous model  
**Baseline:** v4.2.0 hardened implementation  
**Checklist revision:** 1.0  
**Prepared:** 2026-09-22  
**Scope:** Detailed implementation, hardening, verification, operations, supply-chain, migration, and governance work required for the 35 components remaining after the v4.2.0 audit.

## How to use this checklist

- Treat every checkbox as **open until objective evidence exists**. A comment such as “implemented” is not evidence by itself.
- Recommended states in an issue tracker: `OPEN`, `IN_PROGRESS`, `BLOCKED`, `EVIDENCE_READY`, `VERIFIED`, `WAIVED`, `N/A` (with boundary evidence).
- For each checked item, record: implementation commit, test ID/result, artifact/schema version, reviewer, verification date, and evidence location.
- P0 items are release-blocking for reproducible framework/runtime certification. P1 items are production security/concurrency/lifecycle/operability controls. P2 items complete verification depth, supply chain, automation, and governance.
- Maintain the existing v4.2.0 guarantees while implementing this list: bounded waiting, monotonic deadline, race-safe waiter registration, finite poll-set ceiling, hard duration ceiling, structured `PK_POLL_ERROR/1`, stable `ready_indexes`, readiness reset, waiter cleanup, and standalone behavioral verification.

## Global completion gates

- [ ] All 35 component sections have an accountable owner, target release/milestone, dependency mapping, and acceptance evidence plan.
- [ ] All public contracts are versioned and machine-readable; prose is explanatory, not the only source of truth.
- [ ] Every security-sensitive refusal is deterministic, tenant-safe, auditable, and covered by negative tests.
- [ ] Every resource-consuming path has explicit ceilings and cleanup tests.
- [ ] Every production dependency is pinned or bounded by an explicitly tested compatibility policy.
- [ ] Release CI fails closed when mandatory dependencies, integration environments, signatures, schemas, or certification evidence are absent.
- [ ] No checklist item is marked N/A without a written component-boundary justification and reviewer approval.
- [ ] The final release evidence maps every requirement/checklist ID to source, test, artifact, and reviewer approval.

## P0-01 — Pinned `pk_core` runtime/dependency package

**Traceability:** C016, C031, C040, C084, C090, C093, C100  
**Objective:** Make framework-level INV-14 certification reproducible by pinning the exact compatible `pk_core` implementation, its dependency graph, install path, integrity metadata, and execution contract.

### Component-specific engineering checklist

- [ ] **01.01** — Create a canonical dependency declaration that identifies the exact `pk_core` package name, semantic version, source repository or package index, and supported Python interpreter range.
- [ ] **01.02** — Pin `pk_core` to an immutable version and cryptographic digest; reject floating branches, `latest`, unbounded ranges, or mutable local paths in release builds.
- [ ] **01.03** — Generate and commit a deterministic dependency lock that captures all transitive packages, platform markers, hashes, and resolver output needed to recreate the audit environment.
- [ ] **01.04** — Define whether `pk_core` is vendored, installed from an internal index, or bootstrapped externally; document one authoritative production path and one offline/disaster-recovery path.
- [ ] **01.05** — Add a startup compatibility probe that verifies required `pk_core` symbols, schema versions, assessment APIs, and behavioral capabilities before the INV-14 adapter is enabled.
- [ ] **01.06** — Fail closed with a stable machine-readable error when the installed core is absent, wrong-versioned, hash-mismatched, or API-incompatible; do not silently skip certification.
- [ ] **01.07** — Add a clean-room bootstrap test that creates an empty virtual environment, installs only declared dependencies, imports INV-14 and `pk_core`, and executes the complete conformance entry point.
- [ ] **01.08** — Add a dependency-conflict test covering incompatible resolver scenarios and ensure diagnostics identify the conflicting package, requested range, and remediation path.
- [ ] **01.09** — Capture the exact `pk_core` build/version/hash in runtime diagnostics, release evidence, audit events, and the certification report without exposing secrets or local filesystem details.
- [ ] **01.10** — Run the full 100-item framework assessment with the pinned core and archive raw results, normalized results, environment metadata, and pass/fail evidence as release artifacts.
- [ ] **01.11** — Establish an upgrade policy requiring explicit compatibility testing before any `pk_core` version change, including downgrade and rollback verification.
- [ ] **01.12** — Add vulnerability and license scanning for `pk_core` plus transitives, with severity thresholds, approved exception handling, and release blocking for unwaived critical findings.

### A. Requirements and architecture controls

- [ ] **01.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **01.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **01.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **01.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **01.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **01.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **01.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **01.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **01.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **01.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **01.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **01.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **01.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **01.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **01.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **01.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **01.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **01.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **01.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **01.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **01.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **01.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **01.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **01.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **01.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **01.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **01.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **01.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **01.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **01.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **01.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **01.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **01.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P0-02 — Actual WASI 0.2 / `wasi:io` integration adapter

**Traceability:** C021-C030, C031, C082-C084  
**Objective:** Prove the Python reference semantics against real WASI 0.2 pollables through a concrete component-model adapter and executable interoperability fixtures.

### Component-specific engineering checklist

- [ ] **02.01** — Define the target WASI 0.2 world and exact `wasi:io` interfaces consumed or implemented by INV-14, including package/interface versions and world imports/exports.
- [ ] **02.02** — Add authoritative WIT files rather than prose-only interface descriptions, and validate them with the selected WIT parser/toolchain in CI.
- [ ] **02.03** — Generate or hand-author bindings for the supported host/runtime language boundary and record the generator version and command line used.
- [ ] **02.04** — Implement a translation layer between native WASI pollable handles and INV-14 `Pollable`/`PollSet` semantics without leaking Python object identity across the ABI.
- [ ] **02.05** — Define ownership, lifetime, drop, close, and invalid-handle behavior for WASI resources, including double-drop and use-after-drop rejection.
- [ ] **02.06** — Map WASI readiness, timeout, and runtime errors into the canonical `PK_POLL_ERROR/1` taxonomy with deterministic codes and preserved diagnostic context.
- [ ] **02.07** — Define the authoritative mapping from `timeout_ticks` to WASI clock/deadline behavior and verify monotonic-time semantics independent of wall-clock adjustments.
- [ ] **02.08** — Create executable fixtures for zero-ready, immediately-ready, delayed-ready, multiple-ready, timeout, invalid-resource, foreign-owner, and resource-drop scenarios.
- [ ] **02.09** — Test the adapter against at least two independent WASI 0.2-capable runtimes or explicitly document why only one runtime is supportable and how portability will be verified.
- [ ] **02.10** — Prove waiter/resource cleanup after normal return, timeout, cancellation, trap, component termination, and runtime shutdown.
- [ ] **02.11** — Collect interoperability traces that include WIT version, runtime version, adapter version, input pollable count, result indexes, and deterministic error codes.
- [ ] **02.12** — Add an end-to-end release gate that executes the WIT component under a real runtime instead of relying solely on Python unit tests.

### A. Requirements and architecture controls

- [ ] **02.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **02.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **02.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **02.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **02.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **02.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **02.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **02.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **02.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **02.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **02.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **02.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **02.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **02.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **02.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **02.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **02.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **02.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **02.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **02.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **02.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **02.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **02.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **02.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **02.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **02.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **02.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **02.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **02.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **02.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **02.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **02.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **02.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P0-03 — Versioned WIT/schema definitions for `PK_POLL/1`, `PK_POLLABLE/1`, `PK_POLL_ERROR/1`, and `PK_POLL_METRICS/1`

**Traceability:** C021, C022, C026, C029  
**Objective:** Create canonical, machine-readable, versioned interface contracts that are the single source of truth for polling requests, pollables, errors, and metrics.

### Component-specific engineering checklist

- [ ] **03.01** — Create canonical schemas/WIT types for every field in `PK_POLL/1`, `PK_POLLABLE/1`, `PK_POLL_ERROR/1`, and `PK_POLL_METRICS/1`; eliminate undocumented ad-hoc fields.
- [ ] **03.02** — Specify field names, scalar widths, signedness, nullability, collection bounds, ordering guarantees, uniqueness rules, and maximum serialized sizes.
- [ ] **03.03** — Define exact units and ranges for timeout/tick fields, including zero, maximum accepted value, overflow behavior, rounding, and invalid negative/non-integer encodings.
- [ ] **03.04** — Define the error-code enumeration, stable numeric/string identifiers, retryability class, caller-action guidance, and whether details are safe for tenant-visible propagation.
- [ ] **03.05** — Define `ready_indexes` ordering, duplicate semantics, relationship to legacy ready names, and behavior when source pollables are removed or invalidated.
- [ ] **03.06** — Define metric names, types, units, monotonicity, reset semantics, aggregation scope, and label cardinality constraints in `PK_POLL_METRICS/1`.
- [ ] **03.07** — Publish explicit backward/forward compatibility rules: additive-field policy, enum-extension policy, reserved fields, deprecation behavior, and major-version break criteria.
- [ ] **03.08** — Provide canonical valid and invalid serialized fixtures for each schema, including boundary-sized inputs and unknown-field/version cases.
- [ ] **03.09** — Generate validators/code bindings from the canonical schema where possible and prohibit divergent hand-maintained duplicate definitions.
- [ ] **03.10** — Add round-trip encode/decode tests and byte/field-level golden tests so contract drift causes deterministic CI failure.
- [ ] **03.11** — Assign each schema artifact an immutable version and digest and surface both in runtime diagnostics and release evidence.
- [ ] **03.12** — Add a schema-change review gate requiring compatibility analysis, migration notes, regenerated fixtures, and explicit approval for breaking changes.

### A. Requirements and architecture controls

- [ ] **03.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **03.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **03.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **03.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **03.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **03.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **03.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **03.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **03.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **03.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **03.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **03.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **03.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **03.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **03.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **03.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **03.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **03.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **03.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **03.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **03.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **03.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **03.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **03.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **03.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **03.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **03.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **03.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **03.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **03.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **03.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **03.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **03.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P0-04 — INV-15 migration bridge/shim

**Traceability:** C016, C027, C038, C095, C099  
**Objective:** Provide a controlled, observable, reversible path for live consumers to move from the retained INV-14 polling model to the INV-15 asynchronous ABI.

### Component-specific engineering checklist

- [ ] **04.01** — Document a field-by-field and semantic mapping between INV-14 polling concepts and INV-15 operations, including readiness, cancellation, errors, ownership, timeouts, and resource lifetime.
- [ ] **04.02** — Implement a versioned bridge that can expose an INV-14-compatible facade over INV-15 or translate INV-14 calls into INV-15 without ambiguous partial behavior.
- [ ] **04.03** — Define unsupported semantic differences explicitly and reject them with a migration-specific error instead of silently degrading behavior.
- [ ] **04.04** — Add a dual-stack mode in which the same workload can execute through both models under controlled test conditions for parity comparison.
- [ ] **04.05** — Create a migration state machine covering inventory, eligible, canary, dual-run, cutover, rollback, completed, exception, and blocked states.
- [ ] **04.06** — Add per-consumer feature flags or policy controls so migration can be activated incrementally rather than globally.
- [ ] **04.07** — Preserve correlation IDs and observability context across the bridge so parity failures can be traced to a specific consumer and operation.
- [ ] **04.08** — Define rollback criteria and prove that a consumer can revert from INV-15 to INV-14 without orphaning resources or corrupting readiness state during the supported rollback window.
- [ ] **04.09** — Create behavioral parity tests for immediate readiness, delayed readiness, timeout, cancellation, error mapping, ownership rejection, restart, and overload behavior.
- [ ] **04.10** — Measure bridge overhead for latency, CPU, memory, allocations, and handle count; define an approved ceiling so the migration layer does not become a permanent performance liability.
- [ ] **04.11** — Emit migration telemetry identifying bridge use, native INV-15 use, legacy fallback, parity mismatch, rollback, and consumer-level progress.
- [ ] **04.12** — Define the removal condition for the bridge and ensure completed consumers cannot silently regress to INV-14 without an approved waiver.

### A. Requirements and architecture controls

- [ ] **04.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **04.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **04.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **04.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **04.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **04.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **04.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **04.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **04.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **04.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **04.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **04.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **04.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **04.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **04.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **04.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **04.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **04.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **04.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **04.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **04.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **04.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **04.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **04.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **04.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **04.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **04.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **04.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **04.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **04.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **04.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **04.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **04.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-05 — Cancellation contract

**Traceability:** C025  
**Objective:** Add caller-driven cancellation with deterministic race semantics, safe waiter teardown, and canonical cancellation errors.

### Component-specific engineering checklist

- [ ] **05.01** — Define a first-class cancellation token/handle contract with explicit states such as active, cancellation-requested, cancelled, and terminal.
- [ ] **05.02** — Specify precedence for races among readiness, timeout, cancellation, component disable, and underlying resource failure; make the result deterministic and testable.
- [ ] **05.03** — Add a stable cancellation error/outcome code distinct from timeout and operational failure, with documented retry semantics.
- [ ] **05.04** — Register cancellation wakeups atomically with readiness waiters so a cancellation arriving at the registration boundary cannot be lost.
- [ ] **05.05** — Make cancellation idempotent; repeated cancellation requests must not duplicate wakeups, leak waiters, or mutate counters incorrectly.
- [ ] **05.06** — Define whether a ready result that wins the race consumes readiness and whether cancellation after completion is ignored, rejected, or recorded as late.
- [ ] **05.07** — Ensure cancellation propagates through the future WASI/INV-15 adapters without blocking on Python-only constructs.
- [ ] **05.08** — Add metrics for cancellation requests, cancellations won, late cancellations, cancellation latency, and cancellation-related cleanup failures.
- [ ] **05.09** — Add exhaustive boundary tests: pre-cancelled token, cancel-before-wait, cancel-during-wait, cancel-at-timeout-boundary, cancel-after-ready, multi-pollable races, and repeated cancel.
- [ ] **05.10** — Add stress tests proving no lost wakeups, deadlocks, waiter leaks, or negative counters under repeated concurrent signal/clear/cancel operations.
- [ ] **05.11** — Document cancellation ownership and authorization so one tenant/component cannot cancel another principal’s in-flight poll.
- [ ] **05.12** — Include cancellation behavior in the public schema, migration bridge, runbooks, compatibility matrix, and release certification.

### A. Requirements and architecture controls

- [ ] **05.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **05.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **05.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **05.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **05.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **05.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **05.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **05.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **05.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **05.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **05.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **05.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **05.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **05.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **05.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **05.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **05.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **05.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **05.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **05.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **05.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **05.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **05.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **05.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **05.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **05.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **05.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **05.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **05.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **05.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **05.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **05.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **05.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-06 — Backpressure/admission policy beyond a set-size ceiling

**Traceability:** C017, C025, C054, C067  
**Objective:** Prevent overload through bounded concurrency, tenant-aware admission, fairness, deterministic shedding, and saturation observability.

### Component-specific engineering checklist

- [ ] **06.01** — Define explicit ceilings for concurrent polls globally, per tenant, per component, and per process/runtime in addition to the existing per-set size limit.
- [ ] **06.02** — Define queue capacity, queue discipline, maximum queue residence time, and whether queueing is allowed at all for latency-sensitive callers.
- [ ] **06.03** — Select and document a fairness policy such as weighted fair queueing, deficit round robin, or strict quotas; prevent one tenant from monopolizing waiter capacity.
- [ ] **06.04** — Add deterministic overload errors with stable codes and retry guidance; distinguish hard quota violation from transient saturation.
- [ ] **06.05** — If retries are expected, define jitter/backoff guidance or a structured retry-after signal without creating synchronized retry storms.
- [ ] **06.06** — Ensure admission checks occur before expensive waiter allocation or external handle registration to bound memory and file/resource pressure.
- [ ] **06.07** — Define load-shedding order during emergency states and ensure privileged/control-plane traffic cannot accidentally starve all ordinary tenants indefinitely.
- [ ] **06.08** — Add saturation metrics: active polls, queued polls, rejected polls, queue age, per-tenant utilization, fairness deviation, and shedding count.
- [ ] **06.09** — Add burst tests that exceed every configured limit and verify bounded memory, deterministic rejection, recovery, and no starvation after load subsides.
- [ ] **06.10** — Add multi-tenant fairness tests with adversarial high-rate callers and low-rate latency-sensitive callers.
- [ ] **06.11** — Expose all admission parameters through the future versioned configuration schema with bounds, provenance, and atomic update semantics.
- [ ] **06.12** — Define safe defaults that preserve current v4.2.0 behavior for small workloads while preventing unbounded concurrent-wait amplification.

### A. Requirements and architecture controls

- [ ] **06.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **06.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **06.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **06.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **06.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **06.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **06.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **06.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **06.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **06.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **06.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **06.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **06.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **06.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **06.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **06.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **06.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **06.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **06.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **06.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **06.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **06.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **06.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **06.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **06.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **06.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **06.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **06.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **06.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **06.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **06.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **06.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **06.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-07 — Cross-tenant identity/capability integration

**Traceability:** C023, C024, C042, C044, C046  
**Objective:** Bind poll ownership to authenticated, authorized principals rather than caller-provided strings and enforce tenant isolation at the polling boundary.

### Component-specific engineering checklist

- [ ] **07.01** — Define the trusted identity source for runtime components: workload identity, capability token, signed principal assertion, runtime handle, or equivalent authenticated mechanism.
- [ ] **07.02** — Replace raw owner-string trust with a validated principal object whose tenant, component, subject, issuer, audience, scopes, and expiry are cryptographically or runtime-authenticated.
- [ ] **07.03** — Define canonical tenant and component namespaces to prevent look-alike identifiers, Unicode confusion, case ambiguity, and cross-environment collisions.
- [ ] **07.04** — Validate token/assertion issuer, audience, expiry/not-before, signature, key ID, and required capability scopes before pollable ownership checks.
- [ ] **07.05** — Define replay protection and nonce/session semantics if portable bearer capabilities are used.
- [ ] **07.06** — Implement key/capability rotation and revocation handling without requiring a process restart and with deterministic behavior for in-flight polls.
- [ ] **07.07** — Enforce authorization before dereferencing or waiting on foreign pollable resources to avoid side channels and unauthorized timing observation.
- [ ] **07.08** — Return tenant-safe authorization errors that do not disclose foreign resource names, counts, or principal metadata.
- [ ] **07.09** — Emit security audit events for denied cross-owner access, invalid credentials, expired capabilities, replay attempts, and policy mismatches.
- [ ] **07.10** — Add adversarial tests for token tampering, wrong audience, cross-tenant resource injection, stale key IDs, Unicode owner variants, and revoked principals.
- [ ] **07.11** — Define degraded-mode behavior when the identity provider or attestation verifier is unavailable; default to fail closed unless an explicitly approved local trust mode exists.
- [ ] **07.12** — Include identity/capability requirements in the WIT/schema contracts, migration bridge, incident runbook, and compatibility certification.

### A. Requirements and architecture controls

- [ ] **07.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **07.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **07.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **07.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **07.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **07.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **07.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **07.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **07.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **07.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **07.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **07.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **07.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **07.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **07.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **07.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **07.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **07.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **07.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **07.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **07.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **07.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **07.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **07.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **07.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **07.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **07.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **07.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **07.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **07.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **07.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **07.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **07.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-08 — Tamper-evident audit event sink

**Traceability:** C049, C073, C079  
**Objective:** Persist security- and governance-relevant INV-14 events to a verifiable append-only evidence stream with integrity, retention, and access controls.

### Component-specific engineering checklist

- [ ] **08.01** — Define a versioned audit event schema containing event ID, sequence/epoch, timestamp, principal, tenant, component, action, outcome, policy/version, correlation ID, and safe details.
- [ ] **08.02** — Classify mandatory audit events including cross-owner refusal, malformed input, policy disable, waiver use, migration fallback, signing failure, and configuration change.
- [ ] **08.03** — Implement append-only delivery to an approved durable sink; local process memory alone must not satisfy the audit requirement.
- [ ] **08.04** — Add tamper evidence using chained hashes, signed batches, Merkle proofs, WORM storage, or an equivalent verifiable mechanism appropriate to the deployment.
- [ ] **08.05** — Define ordering and clock semantics, including how events are sequenced across restart and how clock regressions are represented.
- [ ] **08.06** — Define at-least-once/at-most-once delivery expectations and deduplication identifiers so retries cannot produce ambiguous forensic records.
- [ ] **08.07** — Protect audit delivery from blocking the poll hot path; use bounded buffering with explicit overflow behavior and never silently drop mandatory security events.
- [ ] **08.08** — Apply redaction/data-minimization rules so audit evidence is useful without containing credentials, raw capability tokens, or unnecessary tenant payload data.
- [ ] **08.09** — Define retention, legal hold, deletion, access-control, and export rules with responsible owner and environment-specific configuration.
- [ ] **08.10** — Provide a verification command/tool that can validate chain/signature integrity and detect deletion, reordering, truncation, or modification.
- [ ] **08.11** — Add failure-injection tests for sink outage, partial write, duplicate delivery, full buffer, restart, corrupted chain, and key rotation.
- [ ] **08.12** — Expose audit-sink health and backlog metrics and alert when mandatory events cannot be durably committed within the approved service objective.

### A. Requirements and architecture controls

- [ ] **08.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **08.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **08.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **08.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **08.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **08.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **08.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **08.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **08.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **08.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **08.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **08.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **08.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **08.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **08.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **08.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **08.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **08.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **08.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **08.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **08.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **08.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **08.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **08.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **08.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **08.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **08.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **08.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **08.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **08.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **08.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **08.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **08.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-09 — Telemetry exporter

**Traceability:** C071-C080  
**Objective:** Export bounded, stable INV-14 operational metrics to an external observability system without introducing high-cardinality or availability coupling.

### Component-specific engineering checklist

- [ ] **09.01** — Define a stable metric namespace and versioned catalog for poll calls, ready outcomes, timeouts, errors, rejections, wait duration, poll-set size, waiter count, and migration use.
- [ ] **09.02** — Specify units, metric type (counter/gauge/histogram), aggregation scope, reset behavior, bucket strategy, and monotonicity for every exported series.
- [ ] **09.03** — Implement at least one supported exporter (for example OpenTelemetry Metrics or Prometheus exposition) behind a narrow adapter interface.
- [ ] **09.04** — Create an explicit label allowlist; prohibit pollable names, raw owner IDs, request IDs, exception strings, or other unbounded labels from metrics.
- [ ] **09.05** — Define cardinality budgets per metric and tests that fail if new labels can exceed the approved bound.
- [ ] **09.06** — Ensure exporter failure, slowness, backpressure, or remote outage cannot block or materially delay `poll()`; use bounded asynchronous export or pull-based exposition.
- [ ] **09.07** — Expose exporter health, dropped samples, queue depth, export latency, and last-success timestamp separately from application metrics.
- [ ] **09.08** — Add histograms for wait duration and set size with buckets chosen from measured behavior rather than arbitrary defaults.
- [ ] **09.09** — Define aggregation across process restart and clarify whether counters are process-local, runtime-local, or fleet-global.
- [ ] **09.10** — Add tests for disabled exporter, endpoint failure, malformed config, metric reset, high concurrency, high event rate, and cardinality attacks.
- [ ] **09.11** — Provide example dashboard queries and recording rules that use only supported labels and units.
- [ ] **09.12** — Version the telemetry contract and require compatibility review before metric rename/removal or semantic changes.

### A. Requirements and architecture controls

- [ ] **09.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **09.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **09.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **09.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **09.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **09.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **09.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **09.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **09.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **09.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **09.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **09.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **09.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **09.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **09.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **09.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **09.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **09.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **09.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **09.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **09.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **09.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **09.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **09.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **09.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **09.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **09.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **09.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **09.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **09.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **09.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **09.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **09.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-10 — Structured logging implementation

**Traceability:** C073, C075, C079  
**Objective:** Produce machine-parseable, correlation-friendly, redacted logs with stable event semantics and bounded diagnostic content.

### Component-specific engineering checklist

- [ ] **10.01** — Define a JSON or equivalent structured log schema with timestamp, severity, event name, component version, tenant-safe principal reference, correlation ID, trace IDs, error code, and outcome.
- [ ] **10.02** — Create a fixed event-name catalog for lifecycle, validation rejection, timeout, readiness, cancellation, policy disable, migration, configuration, and internal fault events.
- [ ] **10.03** — Use stable machine-readable error codes rather than parsing human exception messages in downstream systems.
- [ ] **10.04** — Define a redaction/allowlist policy for details and explicitly ban raw credentials, capability tokens, secrets, full tenant payloads, and unnecessary filesystem paths.
- [ ] **10.05** — Sanitize newline/control characters and structured values to prevent log injection or parser confusion.
- [ ] **10.06** — Add configurable severity and sampling rules while guaranteeing that security refusals, emergency-disable events, and release-critical failures are never sampled away.
- [ ] **10.07** — Bound message/detail sizes and truncate deterministically with an explicit truncation marker to prevent log-amplification attacks.
- [ ] **10.08** — Propagate correlation identifiers from request context and create one when absent, while avoiding globally unique identifiers as metric labels.
- [ ] **10.09** — Include monotonic duration fields for timing-sensitive operations instead of deriving latency from wall-clock timestamps.
- [ ] **10.10** — Add tests that assert exact schema presence, redaction, size bounds, injection safety, invalid Unicode handling, and concurrency-safe emission.
- [ ] **10.11** — Document log retention/transport as an integration responsibility and specify behavior when the logging backend is unavailable.
- [ ] **10.12** — Keep human-readable messages secondary to the stable event schema so operational automation does not depend on prose.

### A. Requirements and architecture controls

- [ ] **10.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **10.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **10.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **10.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **10.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **10.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **10.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **10.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **10.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **10.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **10.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **10.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **10.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **10.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **10.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **10.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **10.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **10.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **10.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **10.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **10.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **10.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **10.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **10.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **10.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **10.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **10.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **10.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **10.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **10.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **10.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **10.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **10.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-11 — Trace-context propagation

**Traceability:** C074  
**Objective:** Preserve distributed tracing context across the poll boundary and adapters while preventing malformed or oversized trace metadata from affecting correctness.

### Component-specific engineering checklist

- [ ] **11.01** — Adopt a documented trace context format, preferably W3C Trace Context for interoperable `traceparent`/`tracestate` handling.
- [ ] **11.02** — Define how inbound trace/span context is supplied to `poll()` or its adapter without changing the core readiness semantics.
- [ ] **11.03** — Create a poll span or span event with stable operation name and attributes for result class, wait duration, set size, timeout/cancel outcome, and component version.
- [ ] **11.04** — Never include pollable names, raw tenant identifiers, secrets, or other high-cardinality/sensitive values as span attributes by default.
- [ ] **11.05** — Propagate context through WASI and INV-15 bridge boundaries using explicit carrier fields or runtime context rather than process-global mutable state.
- [ ] **11.06** — Define asynchronous span-link behavior for readiness signals that originate in a different execution context than the waiting caller.
- [ ] **11.07** — Validate malformed trace headers, oversized baggage, invalid versions, and unsupported flags without failing the functional poll operation.
- [ ] **11.08** — Apply bounded baggage propagation and an allowlist to prevent trace context from becoming an arbitrary data transport.
- [ ] **11.09** — Honor sampling decisions consistently while preserving mandatory audit/security events independently of tracing sampling.
- [ ] **11.10** — Add unit and integration tests for sampled/unsampled contexts, missing context, malformed context, concurrent polls, adapter hops, and cancellation/timeout races.
- [ ] **11.11** — Export tracing-backend health independently so tracing outages do not create false poll failures.
- [ ] **11.12** — Document how trace IDs correlate with structured logs and audit events for incident reconstruction.

### A. Requirements and architecture controls

- [ ] **11.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **11.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **11.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **11.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **11.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **11.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **11.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **11.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **11.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **11.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **11.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **11.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **11.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **11.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **11.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **11.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **11.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **11.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **11.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **11.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **11.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **11.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **11.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **11.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **11.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **11.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **11.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **11.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **11.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **11.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **11.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **11.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **11.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-12 — Emergency disable / policy enforcement hook

**Traceability:** C019, C048, C059, C092  
**Objective:** Provide an authenticated, auditable kill switch that can stop new legacy polling safely while allowing controlled drain and rollback.

### Component-specific engineering checklist

- [ ] **12.01** — Define policy modes such as enabled, warn-only, deny-new, drain, disabled, and emergency-disabled with precise semantics for new and in-flight polls.
- [ ] **12.02** — Implement policy evaluation before waiter/resource allocation so disabled traffic is rejected cheaply and deterministically.
- [ ] **12.03** — Define whether in-flight polls are allowed to complete, cancelled, or failed during each transition and ensure the choice is consistent with migration/rollback guarantees.
- [ ] **12.04** — Make policy updates atomic and thread-safe; no caller should observe partially applied state across related limits or modes.
- [ ] **12.05** — Authenticate and authorize policy changes separately from ordinary poll use, with least-privilege administrative capability.
- [ ] **12.06** — Record every policy change and denied request in the tamper-evident audit sink with actor, reason, previous value, new value, and correlation/change ID.
- [ ] **12.07** — Add break-glass procedures with time-limited authorization, mandatory reason, automatic expiry where feasible, and post-event review.
- [ ] **12.08** — Add propagation/version semantics for multi-process or fleet deployment so stale policy replicas are observable and cannot remain silently enabled.
- [ ] **12.09** — Provide deterministic rollback to the previous approved policy version and test rollback while load is active.
- [ ] **12.10** — Add tests for disable races with ready/timeout/cancel, repeated toggles, stale policy, unauthorized changes, process restart, and drain completion.
- [ ] **12.11** — Expose current policy mode and version in health/diagnostic output without exposing privileged policy content.
- [ ] **12.12** — Link emergency-disable steps directly from alerting and incident runbooks and test them during operational exercises.

### A. Requirements and architecture controls

- [ ] **12.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **12.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **12.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **12.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **12.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **12.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **12.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **12.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **12.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **12.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **12.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **12.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **12.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **12.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **12.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **12.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **12.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **12.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **12.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **12.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **12.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **12.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **12.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **12.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **12.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **12.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **12.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **12.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **12.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **12.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **12.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **12.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **12.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-13 — Per-component migration status registry

**Traceability:** C091, C094, C099  
**Objective:** Maintain an authoritative inventory of all INV-14 consumers and their migration ownership, status, deadline, evidence, and exception state.

### Component-specific engineering checklist

- [ ] **13.01** — Define a machine-readable registry schema with consumer ID, tenant/environment, owning team, current API version, target INV-15 version, migration stage, first/last seen, deadline, and notes.
- [ ] **13.02** — Include waiver/exception reference, expiry date, risk rating, compensating controls, and approving authority when a consumer is permitted to remain on INV-14.
- [ ] **13.03** — Populate the registry from observed telemetry plus declared ownership and reconcile discrepancies rather than relying on manual spreadsheets alone.
- [ ] **13.04** — Define stable migration stages and legal transitions, including blocked and rollback states, and record transition timestamps and actors.
- [ ] **13.05** — Add a CLI/API/report that lists consumers by stage, deadline, owner, recent usage, and exception state without exposing sensitive tenant details to unauthorized viewers.
- [ ] **13.06** — Automatically mark stale records when no usage has been observed for an approved period and require explicit confirmation before declaring migration complete.
- [ ] **13.07** — Prevent completed consumers from silently reappearing on INV-14; generate a regression event and alert when legacy use resumes.
- [ ] **13.08** — Generate deadline and waiver-expiry alerts with escalation to the accountable owner and program governance path.
- [ ] **13.09** — Attach objective migration evidence such as parity-test result, canary window, rollback test, final cutover timestamp, and post-cutover observation window.
- [ ] **13.10** — Version registry updates and retain history so migration claims are auditable over time.
- [ ] **13.11** — Integrate registry status with the emergency-disable policy so enforcement can target unapproved or overdue consumers.
- [ ] **13.12** — Define a final closure workflow that archives completed records while preserving evidence needed for EOL certification.

### A. Requirements and architecture controls

- [ ] **13.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **13.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **13.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **13.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **13.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **13.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **13.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **13.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **13.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **13.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **13.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **13.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **13.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **13.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **13.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **13.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **13.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **13.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **13.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **13.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **13.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **13.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **13.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **13.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **13.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **13.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **13.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **13.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **13.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **13.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **13.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **13.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **13.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-14 — Lifecycle/state model artifact

**Traceability:** C014, C015, C057, C059  
**Objective:** Define an explicit finite-state model for the legacy component lifecycle and enforce legal transitions across deprecation, drain, migration, failure, and quarantine.

### Component-specific engineering checklist

- [ ] **14.01** — Define canonical states including at minimum enabled, deprecated, draining, disabled, migrating, failed, quarantined, and retired; add substates only when operationally necessary.
- [ ] **14.02** — Define every legal transition with trigger, preconditions, authorization, side effects, timeout, completion condition, and failure outcome.
- [ ] **14.03** — Define illegal transitions and require deterministic rejection rather than implicit state coercion.
- [ ] **14.04** — Specify invariants for each state, including whether new polls are accepted, in-flight polls may finish, metrics are exported, and migration operations are permitted.
- [ ] **14.05** — Define state ownership and source of truth for single-process and distributed deployments, including restart and replica reconciliation behavior.
- [ ] **14.06** — Version the state machine and include the active state-model version in audit and diagnostics.
- [ ] **14.07** — Implement transitions atomically with respect to poll admission and waiter registration to prevent drain/disable race inconsistencies.
- [ ] **14.08** — Emit structured lifecycle events and metrics for transition request, success, failure, duration, stale replica, and forced transition.
- [ ] **14.09** — Create a state-transition table and diagram as normative documentation generated from or checked against the machine-readable model.
- [ ] **14.10** — Add exhaustive transition tests that cover every legal edge, every illegal edge, concurrent requests, restart during transition, and rollback.
- [ ] **14.11** — Define time-bounded drain semantics and escalation when drain does not complete due to stuck in-flight operations.
- [ ] **14.12** — Align the lifecycle model with migration registry, EOL policy, emergency-disable behavior, and incident runbooks.

### A. Requirements and architecture controls

- [ ] **14.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **14.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **14.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **14.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **14.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **14.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **14.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **14.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **14.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **14.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **14.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **14.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **14.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **14.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **14.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **14.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **14.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **14.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **14.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **14.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **14.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **14.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **14.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **14.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **14.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **14.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **14.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **14.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **14.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **14.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **14.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **14.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **14.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-15 — Restart/replay semantics

**Traceability:** C057, C095  
**Objective:** Specify and verify crash/restart behavior for ephemeral readiness state, counters, resource identity, and any persisted migration/audit context.

### Component-specific engineering checklist

- [ ] **15.01** — Classify every INV-14 state element as ephemeral, reconstructible, checkpointed, or durable; document why each classification is safe.
- [ ] **15.02** — Define what happens to in-flight polls on process crash: caller-visible disconnect/error, replay, retry, or recovery through a higher layer.
- [ ] **15.03** — Define pollable identity epochs/generations so stale handles from a previous process instance cannot accidentally reference reconstructed resources.
- [ ] **15.04** — Define whether readiness is edge-triggered, level-triggered, or reconstructed from the underlying operation after restart and how missed external events are handled.
- [ ] **15.05** — Define counter reset/persistence semantics so telemetry consumers do not mistake process restart for workload disappearance.
- [ ] **15.06** — If checkpointing is introduced, use atomic writes and versioned records with integrity checks; never restore partially committed waiter state.
- [ ] **15.07** — Make replay operations idempotent or supply stable deduplication identifiers wherever a higher layer can legitimately retry after uncertain completion.
- [ ] **15.08** — Define startup reconciliation against the migration registry, policy state, audit sequence, and configuration version before accepting new polls.
- [ ] **15.09** — Add crash-injection tests at waiter registration, readiness signal, result assembly, timeout boundary, cancellation, policy transition, and telemetry/audit emission points.
- [ ] **15.10** — Add restart-loop tests proving bounded resource growth and correct rejection of stale pollables.
- [ ] **15.11** — Expose process/runtime epoch in diagnostics, logs, traces, and audit events for forensic correlation.
- [ ] **15.12** — Document which guarantees INV-14 cannot provide across crash boundaries and require adjacent layers to compensate explicitly.

### A. Requirements and architecture controls

- [ ] **15.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **15.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **15.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **15.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **15.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **15.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **15.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **15.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **15.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **15.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **15.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **15.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **15.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **15.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **15.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **15.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **15.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **15.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **15.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **15.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **15.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **15.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **15.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **15.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **15.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **15.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **15.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **15.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **15.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **15.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **15.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **15.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **15.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-16 — Clock/tick authority specification

**Traceability:** C011-C013, C022, C031  
**Objective:** Make timeout behavior portable and unambiguous by defining tick units, monotonic clock authority, rounding, limits, and cross-runtime mapping.

### Component-specific engineering checklist

- [ ] **16.01** — Define the normative unit of one `timeout_tick` and whether it is fixed (for example 1 ms) or configurable; prohibit environment-dependent implicit interpretation.
- [ ] **16.02** — Define the authoritative clock source as monotonic/steady rather than wall clock and specify behavior if the runtime cannot provide one.
- [ ] **16.03** — Define conversion from ticks to duration using overflow-safe arithmetic and bounded precision; specify saturation/rejection at configured maximums.
- [ ] **16.04** — Define rounding for fractional host/runtime durations and ensure repeated conversions cannot extend the caller’s requested deadline.
- [ ] **16.05** — Define timeout zero semantics, maximum timeout semantics, and the relationship between configured maximum ticks and the hard 60-second v4.2.0 ceiling.
- [ ] **16.06** — Define behavior under wall-clock jumps, NTP corrections, suspend/resume, VM pause, host migration, and monotonic-clock anomalies.
- [ ] **16.07** — Define whether timeout is measured from API entry, post-validation, waiter registration, or first blocking wait and keep the choice consistent across adapters.
- [ ] **16.08** — Expose the effective tick duration and clock implementation in runtime diagnostics and release evidence.
- [ ] **16.09** — Add boundary tests for zero, one tick, maximum tick, one-past-maximum, integer-width limits, conversion rounding, and artificially advanced clocks.
- [ ] **16.10** — Add deterministic fake-clock tests so timeout races can be validated without flaky wall-time sleeps.
- [ ] **16.11** — Verify equivalent timeout behavior in Python, WASI adapter, and INV-15 migration bridge within an approved tolerance.
- [ ] **16.12** — Version any change to tick semantics as a contract change and require migration analysis before deployment.

### A. Requirements and architecture controls

- [ ] **16.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **16.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **16.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **16.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **16.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **16.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **16.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **16.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **16.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **16.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **16.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **16.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **16.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **16.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **16.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **16.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **16.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **16.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **16.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **16.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **16.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **16.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **16.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **16.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **16.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **16.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **16.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **16.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **16.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **16.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **16.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **16.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **16.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-17 — Owner/escalation metadata

**Traceability:** C009, C091, C097  
**Objective:** Make operational and engineering accountability explicit through versioned ownership, support, escalation, and service-catalog metadata.

### Component-specific engineering checklist

- [ ] **17.01** — Add a machine-readable ownership file naming the accountable engineering team, service owner role, repository maintainers, and security owner role.
- [ ] **17.02** — Add CODEOWNERS or equivalent review enforcement for polling implementation, schemas, security policy, release pipeline, and EOL artifacts.
- [ ] **17.03** — Define on-call/paging integration by service identifier or rotation reference rather than embedding personal contact details in source control.
- [ ] **17.04** — Define an escalation ladder for Sev-1/Sev-2 incidents, security events, migration blockers, expired waivers, and unsupported-runtime failures.
- [ ] **17.05** — Define support hours, response targets, handoff boundaries, and which adjacent team owns `pk_core`, runtime/WASI, telemetry, and migration dependencies.
- [ ] **17.06** — Add links/identifiers for service catalog, runbook, dashboard, incident channel/process, and change-management system.
- [ ] **17.07** — Version metadata changes and retain enough history to determine who owned the component at a past release or incident date.
- [ ] **17.08** — Validate ownership references in CI so deleted teams, missing runbooks, or invalid catalog IDs fail the metadata check.
- [ ] **17.09** — Add a quarterly or release-based ownership recertification requirement with recorded approval.
- [ ] **17.10** — Ensure migration registry entries map each consumer to an accountable owner rather than only the central INV-14 owner.
- [ ] **17.11** — Define the escalation path when no consumer owner can be identified; treat unknown ownership as a migration blocker.
- [ ] **17.12** — Keep personal names optional and prefer stable organizational roles/identifiers to avoid stale or privacy-sensitive metadata.

### A. Requirements and architecture controls

- [ ] **17.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **17.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **17.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **17.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **17.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **17.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **17.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **17.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **17.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **17.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **17.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **17.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **17.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **17.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **17.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **17.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **17.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **17.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **17.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **17.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **17.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **17.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **17.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **17.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **17.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **17.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **17.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **17.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **17.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **17.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **17.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **17.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **17.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-18 — Architecture Decision Record (ADR)

**Traceability:** C010, C098, C099  
**Objective:** Record the rationale, constraints, risks, alternatives, migration strategy, and retirement criteria for retaining INV-14 as a legacy compatibility component.

### Component-specific engineering checklist

- [ ] **18.01** — Create a numbered, immutable ADR with status, date, deciders/approvers, context, decision, consequences, and links to superseding decisions.
- [ ] **18.02** — Document why INV-14 remains necessary after INV-15 exists and identify the concrete consumers or compatibility constraints that justify retention.
- [ ] **18.03** — Enumerate considered alternatives such as immediate removal, direct INV-15 migration, compatibility shim, or runtime-native polling and explain why each was accepted/rejected.
- [ ] **18.04** — Document the security model, tenant-isolation assumptions, in-memory state boundary, and non-goals so future features do not silently expand scope.
- [ ] **18.05** — Document performance and resource constraints including poll-set ceiling, hard timeout, expected concurrency, and known adapter overhead.
- [ ] **18.06** — Document failure and restart semantics, cancellation/backpressure gaps, and which missing components are release blockers versus follow-on hardening.
- [ ] **18.07** — Define migration milestones, rollback conditions, waiver policy, and objective EOL/removal criteria.
- [ ] **18.08** — Include compatibility assumptions for `pk_core`, Python, WASI 0.2, INV-13, INV-15, and GAP-15.
- [ ] **18.09** — Document observability and audit requirements needed before broader production deployment.
- [ ] **18.10** — Link the ADR to the threat model, lifecycle state model, configuration schema, runbooks, and release checklist.
- [ ] **18.11** — Require architecture/security review for changes that alter the ADR’s assumptions, public contract, lifecycle, or EOL plan.
- [ ] **18.12** — Mark superseded ADRs explicitly without deleting historical decisions needed for auditability.

### A. Requirements and architecture controls

- [ ] **18.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **18.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **18.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **18.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **18.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **18.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **18.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **18.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **18.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **18.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **18.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **18.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **18.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **18.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **18.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **18.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **18.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **18.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **18.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **18.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **18.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **18.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **18.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **18.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **18.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **18.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **18.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **18.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **18.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **18.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **18.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **18.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **18.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P1-19 — Compatibility matrix

**Traceability:** C027, C084, C093  
**Objective:** Define and continuously verify the supported combinations of interpreter, core, runtime, architecture, interface, and adjacent INV/GAP versions.

### Component-specific engineering checklist

- [ ] **19.01** — Define matrix dimensions for Python version, `pk_core` version, operating system where applicable, CPU architecture, WASI runtime/version, WIT package version, INV-13, INV-15, and GAP-15.
- [ ] **19.02** — Classify each combination as supported, conditionally supported, deprecated, unsupported, or not tested; do not equate untested with supported.
- [ ] **19.03** — Define minimum and maximum versions plus explicit exclusions for known-bad combinations.
- [ ] **19.04** — Automate representative matrix jobs in CI and schedule broader/nightly coverage for expensive runtime/architecture combinations.
- [ ] **19.05** — Include x86_64 and arm64 where the target deployment uses both, or document the hardware constraint that makes one architecture non-applicable.
- [ ] **19.06** — Run positive interoperability tests on supported cells and negative startup/diagnostic tests for explicitly unsupported cells.
- [ ] **19.07** — Capture exact toolchain/runtime versions and hashes in each matrix test result so results are reproducible.
- [ ] **19.08** — Add downgrade and rollback tests for supported prior versions when operational rollback requires them.
- [ ] **19.09** — Publish the matrix as generated release documentation sourced from machine-readable metadata to avoid drift.
- [ ] **19.10** — Define the review process for adding/removing supported cells, including migration notice and EOL implications.
- [ ] **19.11** — Use the release verifier to reject packages whose declared versions fall outside the tested support matrix.
- [ ] **19.12** — Archive matrix evidence with each release rather than relying only on the current CI dashboard state.

### A. Requirements and architecture controls

- [ ] **19.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **19.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **19.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **19.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **19.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **19.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **19.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **19.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **19.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **19.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **19.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **19.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **19.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **19.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **19.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **19.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **19.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **19.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **19.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **19.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **19.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **19.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **19.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **19.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **19.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **19.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **19.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **19.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **19.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **19.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **19.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **19.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **19.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-20 — Real adjacent-layer integration tests

**Traceability:** C030, C083, C089  
**Objective:** Exercise INV-14 against actual INV-13, INV-15, and GAP-15 implementations or version-pinned test doubles that enforce their real contracts.

### Component-specific engineering checklist

- [ ] **20.01** — Pin exact adjacent-layer versions and record source/build hashes for INV-13 system interface, INV-15 async ABI, and GAP-15 runtime certification fixtures.
- [ ] **20.02** — Create end-to-end setup code that instantiates real boundary objects rather than mocking the entire interface under test.
- [ ] **20.03** — Cover successful immediate readiness, delayed readiness, multiple-ready results, timeout, malformed input, ownership refusal, cancellation, and overload paths across layer boundaries.
- [ ] **20.04** — Validate canonical error propagation and ensure adjacent layers do not collapse distinct INV-14 error codes into ambiguous generic failures.
- [ ] **20.05** — Validate correlation/trace/audit identifiers survive each boundary and can reconstruct a complete operation path.
- [ ] **20.06** — Exercise lifecycle events: start, drain, disable, migration cutover, rollback, restart, and teardown with adjacent components active.
- [ ] **20.07** — Inject version mismatch and unsupported-feature combinations to verify fail-closed compatibility handling.
- [ ] **20.08** — Assert resource cleanup across layers, including dropped handles, waiter removal, cancelled operations, process teardown, and failed initialization.
- [ ] **20.09** — Run tests in deterministic isolated environments with no undeclared network, package-index, or local-state dependency.
- [ ] **20.10** — Add CI jobs that fail the release when any required adjacent-layer test is skipped, unavailable, or running against an unapproved version.
- [ ] **20.11** — Publish machine-readable integration results with environment metadata, component hashes, test IDs, and artifacts required for certification.
- [ ] **20.12** — Maintain a reduced smoke subset for every commit and a broader fault/soak integration suite for release candidates.

### A. Requirements and architecture controls

- [ ] **20.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **20.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **20.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **20.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **20.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **20.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **20.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **20.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **20.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **20.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **20.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **20.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **20.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **20.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **20.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **20.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **20.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **20.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **20.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **20.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **20.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **20.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **20.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **20.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **20.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **20.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **20.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **20.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **20.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **20.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **20.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **20.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **20.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-21 — WIT/protocol contract tests

**Traceability:** C029, C082  
**Objective:** Prove that serialized contracts and WIT bindings conform exactly to the versioned schemas, including malformed, boundary, compatibility, and round-trip cases.

### Component-specific engineering checklist

- [ ] **21.01** — Create golden fixtures for every public request, response, pollable, error, and metrics type using canonical supported encodings.
- [ ] **21.02** — Validate encode/decode round trips preserve semantic values and any explicitly guaranteed ordering without depending on incidental serializer behavior.
- [ ] **21.03** — Add malformed-fixture cases for missing required fields, duplicate fields where applicable, invalid enums, wrong scalar types, out-of-range integers, oversized collections, and invalid UTF encodings.
- [ ] **21.04** — Add unknown-field and unknown-enum tests that enforce the documented forward-compatibility policy.
- [ ] **21.05** — Add version-negotiation tests for current, prior supported, future-unknown, and explicitly incompatible major versions.
- [ ] **21.06** — Validate `ready_indexes` and ready-name correlation, including duplicate-name rejection and maximum poll-set boundaries.
- [ ] **21.07** — Validate error-schema stability: every documented code must serialize, deserialize, and preserve retryability/classification metadata.
- [ ] **21.08** — Validate metrics-schema units, numeric bounds, monotonic fields, and absence of forbidden high-cardinality labels.
- [ ] **21.09** — Round-trip generated bindings from every supported language/runtime used by the WASI adapter, not just Python representations.
- [ ] **21.10** — Hash golden fixtures and review intentional changes; unexpected fixture drift must fail CI.
- [ ] **21.11** — Add differential tests between reference implementation and runtime adapter for identical contract inputs.
- [ ] **21.12** — Publish a conformance command that downstream consumers can run against their bindings before integration.

### A. Requirements and architecture controls

- [ ] **21.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **21.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **21.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **21.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **21.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **21.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **21.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **21.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **21.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **21.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **21.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **21.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **21.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **21.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **21.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **21.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **21.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **21.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **21.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **21.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **21.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **21.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **21.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **21.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **21.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **21.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **21.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **21.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **21.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **21.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **21.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **21.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **21.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-22 — Fuzz harness

**Traceability:** C050, C085  
**Objective:** Continuously discover parser, validation, state-machine, timeout, ownership, and resource-lifetime defects using reproducible fuzzing and minimized regression corpora.

### Component-specific engineering checklist

- [ ] **22.01** — Build separate fuzz targets for poll-set construction, pollable identity/name parsing, timeout values, error/schema decoding, configuration decoding, and cross-owner inputs.
- [ ] **22.02** — Use grammar/schema-aware generators so valid structures receive deep semantic mutation instead of spending most cycles on trivially invalid syntax.
- [ ] **22.03** — Seed the corpus with all golden protocol fixtures, boundary cases, prior bugs, race reproductions, and maximum-size valid objects.
- [ ] **22.04** — Generate pathological cases including duplicate names, huge collections, extreme integers, invalid Unicode, embedded control characters, type confusion, and stale handles.
- [ ] **22.05** — Instrument invariants such as no crash, no deadlock, bounded allocation, deterministic validation code, waiter cleanup, and unchanged foreign resources.
- [ ] **22.06** — Apply strict per-input time and memory limits so hangs and amplification bugs are detected as failures.
- [ ] **22.07** — Persist failing seeds, minimize them automatically where tooling supports it, and add minimized cases to a permanent regression corpus.
- [ ] **22.08** — Record fuzzer engine/version, random seed, corpus digest, target version, and sanitizer/runtime settings for reproducibility.
- [ ] **22.09** — Run short fuzz budgets on pull requests and longer scheduled/release-candidate campaigns with defined minimum execution counts or CPU-hours.
- [ ] **22.10** — Integrate coverage reporting to identify unexercised validation and error branches rather than relying only on crash counts.
- [ ] **22.11** — Add triage rules for duplicate findings, nondeterministic failures, security severity, and release-blocking criteria.
- [ ] **22.12** — Ensure fuzz inputs cannot access external networks, arbitrary files, or production credentials during CI execution.

### A. Requirements and architecture controls

- [ ] **22.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **22.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **22.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **22.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **22.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **22.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **22.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **22.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **22.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **22.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **22.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **22.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **22.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **22.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **22.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **22.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **22.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **22.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **22.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **22.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **22.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **22.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **22.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **22.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **22.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **22.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **22.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **22.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **22.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **22.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **22.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **22.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **22.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-23 — Dedicated concurrency model checking/race tooling

**Traceability:** C086  
**Objective:** Demonstrate race safety beyond ordinary thread tests by systematically exploring signal/clear/wait/cancel/policy interleavings and checking linearizable outcomes.

### Component-specific engineering checklist

- [ ] **23.01** — Define a small formal/reference state model for pollable readiness, waiter registration, signal, clear, cancellation, timeout, and terminal completion.
- [ ] **23.02** — Define linearization points for `signal()`, `clear()`, waiter registration, cancellation, and result return so ambiguous races have a testable specification.
- [ ] **23.03** — Use a systematic scheduler/model checker where available, or a deterministic interleaving harness that can force operations at critical synchronization points.
- [ ] **23.04** — Cover signal-before-register, signal-during-register, signal-after-snapshot, clear-vs-signal, cancel-vs-ready, timeout-vs-ready, and disable-vs-register interleavings.
- [ ] **23.05** — Exercise multiple poll sets waiting on the same pollable and one poll set containing many independently signaled pollables.
- [ ] **23.06** — Check invariants: no lost wakeup, no duplicate terminal result, no waiter leak, no deadlock, no unauthorized cross-owner wake, and stable ready-index ordering.
- [ ] **23.07** — Add high-iteration stress tests on multicore hosts with randomized operation timing and process-level repetition.
- [ ] **23.08** — Run race-detection or thread-sanitizer-equivalent tooling for any native bindings introduced by WASI/FFI adapters.
- [ ] **23.09** — Capture failing schedules/seeds so every concurrency failure is exactly replayable in CI.
- [ ] **23.10** — Add memory/resource accounting assertions around waiter registration and teardown to detect leaks hidden by functional success.
- [ ] **23.11** — Include restart and policy transitions in extended concurrency campaigns once those components are implemented.
- [ ] **23.12** — Define a release threshold requiring zero unexplained concurrency failures across the approved stress/model-checking budget.

### A. Requirements and architecture controls

- [ ] **23.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **23.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **23.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **23.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **23.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **23.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **23.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **23.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **23.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **23.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **23.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **23.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **23.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **23.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **23.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **23.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **23.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **23.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **23.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **23.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **23.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **23.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **23.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **23.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **23.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **23.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **23.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **23.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **23.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **23.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **23.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **23.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **23.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-24 — Benchmark suite and approved thresholds

**Traceability:** C061-C070, C088  
**Objective:** Quantify latency, throughput, CPU, memory, fan-out, startup, and resource costs and prevent statistically meaningful regressions.

### Component-specific engineering checklist

- [ ] **24.01** — Create a benchmark harness that separates validation cost, waiter-registration cost, blocking wait, wake fan-out, result assembly, and adapter overhead.
- [ ] **24.02** — Measure p50, p90, p95, p99, p99.9 where sample size supports it, plus maximum observed latency and confidence/variance information.
- [ ] **24.03** — Benchmark poll-set sizes across a geometric range from 1 to the configured maximum, including sparse-ready and all-ready cases.
- [ ] **24.04** — Benchmark timeout-only calls separately from immediate-ready and delayed-ready calls to expose timer/waiter overhead.
- [ ] **24.05** — Measure throughput under increasing concurrency until saturation and record active polls, rejection rate, queueing, and fairness when admission control exists.
- [ ] **24.06** — Measure CPU time, wall time, peak/resident memory, allocations where practical, thread count, handle count, and waiter cleanup cost.
- [ ] **24.07** — Benchmark WASI adapter and migration bridge overhead relative to the Python/reference baseline and define acceptable overhead budgets.
- [ ] **24.08** — Control warm-up, CPU affinity where appropriate, power policy, background load, interpreter/runtime version, and hardware metadata for reproducibility.
- [ ] **24.09** — Define approved regression thresholds per metric and load shape; do not use one global percentage for all benchmarks.
- [ ] **24.10** — Use statistical comparison or repeated-run tolerance so normal noise does not create flaky release gates.
- [ ] **24.11** — Archive raw benchmark samples and environment metadata for each release candidate and plot trends over time.
- [ ] **24.12** — Include performance thresholds in the release verifier once a stable baseline has been approved.

### A. Requirements and architecture controls

- [ ] **24.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **24.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **24.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **24.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **24.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **24.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **24.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **24.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **24.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **24.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **24.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **24.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **24.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **24.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **24.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **24.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **24.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **24.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **24.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **24.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **24.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **24.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **24.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **24.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **24.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **24.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **24.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **24.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **24.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **24.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **24.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **24.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **24.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-25 — Soak/burst/fleet-scale test harness

**Traceability:** C063, C088  
**Objective:** Validate long-duration stability, overload recovery, multi-tenant fairness, and high-cardinality operational behavior under realistic fleet-scale patterns.

### Component-specific engineering checklist

- [ ] **25.01** — Define representative fleet profiles for number of consumers, tenants, pollables per set, poll frequency, readiness distribution, timeout distribution, and migration mix.
- [ ] **25.02** — Create a long-duration soak scenario with sustained mixed ready/timeout traffic and repeated signal/clear cycles sufficient to expose slow leaks.
- [ ] **25.03** — Create burst scenarios that exceed normal arrival rates and configured admission limits by controlled multiples.
- [ ] **25.04** — Include high-cardinality consumer inventories while keeping telemetry label cardinality bounded according to the exporter contract.
- [ ] **25.05** — Measure memory, handles, waiter objects, threads, GC pressure, CPU, latency percentiles, rejection rate, and recovery time throughout the run.
- [ ] **25.06** — Assert that resource use returns to a defined steady-state envelope after bursts and after all callers disconnect.
- [ ] **25.07** — Exercise process restart and rolling-restart cycles during load once restart semantics are implemented.
- [ ] **25.08** — Include mixed-tenant load with abusive and well-behaved callers to verify quota/fairness isolation.
- [ ] **25.09** — Inject telemetry/audit backend slowdown during soak to prove observability paths remain non-blocking and bounded.
- [ ] **25.10** — Define pass/fail limits for leak rate, latency drift, error rate, backlog growth, and time-to-recover rather than relying on visual inspection.
- [ ] **25.11** — Archive time-series evidence and environment/workload definitions so a failed soak can be replayed.
- [ ] **25.12** — Run a shorter burst suite per release and a longer soak on a scheduled cadence or before high-risk runtime changes.

### A. Requirements and architecture controls

- [ ] **25.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **25.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **25.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **25.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **25.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **25.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **25.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **25.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **25.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **25.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **25.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **25.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **25.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **25.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **25.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **25.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **25.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **25.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **25.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **25.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **25.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **25.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **25.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **25.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **25.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **25.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **25.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **25.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **25.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **25.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **25.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **25.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **25.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-26 — Fault-injection harness

**Traceability:** C060, C089  
**Objective:** Verify bounded, diagnosable recovery under process, runtime, clock, dependency, configuration, and control-plane faults.

### Component-specific engineering checklist

- [ ] **26.01** — Create a fault catalog covering process kill, thread stall, runtime trap, dependency absence/version mismatch, telemetry outage, audit outage, corrupted config, and identity-verifier failure.
- [ ] **26.02** — Include clock faults such as wall-clock jumps, monotonic-source failure simulation, suspend/resume, and deadline advancement using the fake clock abstraction.
- [ ] **26.03** — Inject resource faults: invalid/stale pollable, dropped handle, waiter-registration failure, exhausted admission capacity, and cleanup failure.
- [ ] **26.04** — Where networked adjacent layers exist, inject partition, latency, reconnect, DNS/service-discovery failure, and partial control-plane availability.
- [ ] **26.05** — Define expected behavior for each fault: fail closed/open, retry, degrade, drain, reject, restart, or escalate; no scenario should depend on undefined behavior.
- [ ] **26.06** — Assert stable error codes, bounded recovery time, no resource leaks, no cross-tenant exposure, and complete audit/diagnostic evidence.
- [ ] **26.07** — Use deterministic fault triggers and seeds so CI can reproduce the exact failure point.
- [ ] **26.08** — Test faults at critical boundaries including before admission, after waiter registration, during signal, before result return, and during policy/migration transition.
- [ ] **26.09** — Validate that emergency disable remains usable under degraded telemetry or migration dependencies.
- [ ] **26.10** — Capture recovery-time and data/state-consistency metrics and compare them with approved objectives.
- [ ] **26.11** — Promote every production incident root cause into a permanent fault-injection regression scenario when technically feasible.
- [ ] **26.12** — Keep destructive fault tests isolated from developer machines and production credentials through dedicated ephemeral environments.

### A. Requirements and architecture controls

- [ ] **26.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **26.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **26.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **26.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **26.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **26.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **26.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **26.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **26.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **26.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **26.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **26.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **26.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **26.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **26.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **26.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **26.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **26.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **26.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **26.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **26.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **26.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **26.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **26.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **26.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **26.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **26.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **26.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **26.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **26.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **26.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **26.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **26.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-27 — CI release pipeline

**Traceability:** C070, C090, C100  
**Objective:** Turn the repository’s verification requirements into deterministic, fail-closed automation executed on every change and release candidate.

### Component-specific engineering checklist

- [ ] **27.01** — Add a version-controlled CI workflow with pinned runner/tool versions or immutable container images.
- [ ] **27.02** — Run syntax/bytecode compilation and import smoke tests for all supported Python versions and fail on warnings selected by policy.
- [ ] **27.03** — Run standalone behavioral tests in normal and optimized (`-O`) modes exactly as performed during the v4.2.0 audit.
- [ ] **27.04** — Install the pinned `pk_core` and execute the full 100-item framework conformance gate; skipped or unavailable required tests must fail the release job.
- [ ] **27.05** — Run WIT/schema validation, protocol golden tests, adjacent integration tests, and real WASI runtime tests as required jobs.
- [ ] **27.06** — Run static analysis, dependency vulnerability/license checks, secret scanning, and configuration/schema validation.
- [ ] **27.07** — Run concurrency, fuzz-smoke, benchmark-smoke, and fault-smoke jobs with longer scheduled variants outside the fast path.
- [ ] **27.08** — Generate SBOM, provenance, checksums, test reports, compatibility matrix result, and release manifest from the exact build under test.
- [ ] **27.09** — Sign release artifacts only after all required gates succeed and ensure signing credentials are isolated to protected release contexts.
- [ ] **27.10** — Configure branch/release protection so required jobs cannot be bypassed by ordinary contributors; document emergency override governance.
- [ ] **27.11** — Upload immutable build/test evidence with retention sufficient for incident and certification needs.
- [ ] **27.12** — Add a final `verify_release` job that downloads the produced artifact into a clean environment and independently validates hashes, signatures, versions, dependencies, and required evidence.

### A. Requirements and architecture controls

- [ ] **27.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **27.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **27.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **27.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **27.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **27.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **27.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **27.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **27.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **27.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **27.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **27.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **27.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **27.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **27.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **27.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **27.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **27.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **27.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **27.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **27.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **27.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **27.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **27.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **27.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **27.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **27.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **27.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **27.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **27.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **27.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **27.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **27.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-28 — Dependency/SBOM/provenance artifacts

**Traceability:** C045, C094  
**Objective:** Make every release’s software composition and build origin inspectable, reproducible, policy-checked, and cryptographically bound to the released artifact.

### Component-specific engineering checklist

- [ ] **28.01** — Create a complete dependency lock for direct and transitive Python/runtime/tool dependencies used to build and certify INV-14.
- [ ] **28.02** — Generate an SBOM in a standard format such as SPDX or CycloneDX containing package name, version, supplier/source, license, hashes, and dependency relationships.
- [ ] **28.03** — Include vendored code, generated bindings, WIT tooling, native/runtime libraries, and build containers where they materially affect the release.
- [ ] **28.04** — Generate build provenance that records source revision, dirty-tree status, builder identity, toolchain versions, build commands, input digests, and output digests.
- [ ] **28.05** — Bind SBOM and provenance to the exact archive checksum and release version; prevent detached evidence from being reused with a different binary/package.
- [ ] **28.06** — Run vulnerability scanning against the locked dependency set and define severity/age thresholds that block release absent a valid waiver.
- [ ] **28.07** — Run license policy checks and capture attribution/notice obligations in the release evidence.
- [ ] **28.08** — Define update cadence for vulnerability databases and how previously released artifacts are re-evaluated when new vulnerabilities are disclosed.
- [ ] **28.09** — Archive dependency sources or approved mirrors needed for reproducible/offline rebuild where organizational policy requires it.
- [ ] **28.10** — Compare two clean builds for reproducibility where feasible and document any known nondeterministic fields.
- [ ] **28.11** — Version the SBOM/provenance schema/tooling and verify generated documents in CI before signing.
- [ ] **28.12** — Publish a verification procedure that lets an operator trace a deployed INV-14 package back to source, dependency graph, build job, and signature.

### A. Requirements and architecture controls

- [ ] **28.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **28.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **28.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **28.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **28.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **28.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **28.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **28.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **28.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **28.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **28.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **28.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **28.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **28.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **28.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **28.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **28.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **28.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **28.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **28.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **28.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **28.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **28.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **28.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **28.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **28.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **28.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **28.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **28.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **28.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **28.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **28.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **28.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-29 — Artifact signing and verification hook

**Traceability:** C045  
**Objective:** Cryptographically authenticate release artifacts and provide a fail-closed verification path with key rotation and revocation support.

### Component-specific engineering checklist

- [ ] **29.01** — Define the signing format and trust model: detached signature, signed manifest, Sigstore-style identity, organizational PKI, or equivalent approved mechanism.
- [ ] **29.02** — Sign the release archive, manifest, SBOM, provenance, and optionally critical schemas as one coherently verifiable release set.
- [ ] **29.03** — Keep private signing keys out of developer workstations and general CI jobs; use protected release credentials, HSM/KMS, or ephemeral workload identity where available.
- [ ] **29.04** — Define trusted signer identities/keys, trust roots, key IDs, validity periods, and environment separation for development versus production releases.
- [ ] **29.05** — Provide a one-command verifier that checks signature, checksum, manifest membership, release version consistency, and trust-policy validity before installation/use.
- [ ] **29.06** — Fail closed on missing signature, unknown signer, revoked key, expired policy where applicable, hash mismatch, or manifest inconsistency.
- [ ] **29.07** — Define key rotation and emergency revocation procedures and prove old/new trust overlap during planned rotations.
- [ ] **29.08** — Add timestamp/transparency evidence where supported so signatures remain auditable after key expiry/rotation.
- [ ] **29.09** — Add positive and negative verification tests for altered archive bytes, altered manifest, wrong signer, revoked signer, missing evidence, and replayed metadata.
- [ ] **29.10** — Record signing event metadata in the release audit/provenance evidence without exposing private key material.
- [ ] **29.11** — Integrate signature verification into deployment/bootstrap and the release verifier rather than leaving it as optional operator documentation.
- [ ] **29.12** — Document how offline/disconnected environments obtain and refresh trusted public verification material.

### A. Requirements and architecture controls

- [ ] **29.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **29.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **29.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **29.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **29.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **29.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **29.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **29.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **29.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **29.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **29.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **29.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **29.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **29.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **29.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **29.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **29.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **29.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **29.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **29.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **29.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **29.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **29.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **29.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **29.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **29.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **29.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **29.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **29.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **29.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **29.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **29.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **29.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-30 — Configuration schema/provenance

**Traceability:** C033-C038  
**Objective:** Move safety-critical limits and policies from ad-hoc constructor parameters into validated, versioned, attributable, atomically applied configuration.

### Component-specific engineering checklist

- [ ] **30.01** — Define a canonical configuration schema covering tick duration, maximum timeout, poll-set size, concurrency/admission limits, policy mode, telemetry, audit, and migration controls.
- [ ] **30.02** — Specify type, unit, default, minimum, maximum, required/optional status, mutability, and security sensitivity for every field.
- [ ] **30.03** — Define configuration-layer precedence (built-in defaults, site policy, environment, deployment, per-component overrides) and prohibit ambiguous duplicate sources.
- [ ] **30.04** — Attach provenance metadata such as schema version, configuration version, author/source, creation time, approval/change ID, and activation time.
- [ ] **30.05** — Validate the complete candidate configuration before activation and reject unknown fields or invalid combinations according to the compatibility policy.
- [ ] **30.06** — Apply multi-field updates atomically so callers cannot observe transient combinations that violate safety invariants.
- [ ] **30.07** — Define which fields are dynamic and which require drain/restart; refuse unsafe live mutation explicitly.
- [ ] **30.08** — Retain the last known-good configuration and support deterministic rollback with audit evidence.
- [ ] **30.09** — Protect configuration changes with authenticated authorization distinct from ordinary poll callers.
- [ ] **30.10** — Use secret references rather than inline secret values if future integrations require credentials; never expose resolved secrets in diagnostics.
- [ ] **30.11** — Add schema, boundary, precedence, atomicity, rollback, stale-version, concurrent-update, and corrupted-config tests.
- [ ] **30.12** — Expose the active configuration version and safe non-secret summary in diagnostics, telemetry, and incident evidence.

### A. Requirements and architecture controls

- [ ] **30.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **30.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **30.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **30.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **30.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **30.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **30.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **30.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **30.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **30.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **30.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **30.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **30.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **30.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **30.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **30.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **30.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **30.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **30.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **30.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **30.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **30.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **30.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **30.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **30.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **30.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **30.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **30.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **30.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **30.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **30.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **30.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **30.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-31 — Secret-handling/redaction policy

**Traceability:** C039, C047, C075  
**Objective:** Prevent future telemetry, diagnostics, adapters, and policy integrations from leaking credentials or tenant-sensitive data as INV-14 evolves.

### Component-specific engineering checklist

- [ ] **31.01** — Create a data-classification table for all current and anticipated fields across requests, identity context, logs, traces, metrics, audit, config, exceptions, and crash reports.
- [ ] **31.02** — Explicitly designate secrets/tokens/private keys/passwords as prohibited from polling payloads and observability fields unless a separate approved secure channel requires them.
- [ ] **31.03** — Use field allowlists for structured logging/audit rather than relying only on pattern-based redaction after serialization.
- [ ] **31.04** — If pattern redaction is used as defense in depth, define tested patterns for known credential formats and make redaction happen before data leaves process memory.
- [ ] **31.05** — Never log raw capability tokens, signature material, bearer headers, environment secrets, or resolved secret-manager values.
- [ ] **31.06** — Define handling for tenant identifiers and pollable names: hashed/pseudonymous, truncated, omitted, or access-controlled according to operational need.
- [ ] **31.07** — Bound exception/detail serialization and strip local paths, stack variables, and object representations that may contain sensitive values before tenant-visible propagation.
- [ ] **31.08** — Add canary-secret tests that inject known fake credentials into every observability/error path and assert they never appear in output artifacts.
- [ ] **31.09** — Add tests for multiline values, Unicode, encoded/base64 secrets, nested structures, and oversized fields to prevent redaction bypass.
- [ ] **31.10** — Define retention/access policies for diagnostic artifacts that may contain sensitive metadata even after secret stripping.
- [ ] **31.11** — Require security review for any new field added to public error, log, trace, audit, metrics, or configuration schemas.
- [ ] **31.12** — Document incident steps for accidental secret exposure, including sink quarantine, credential rotation, evidence preservation, and notification path.

### A. Requirements and architecture controls

- [ ] **31.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **31.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **31.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **31.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **31.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **31.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **31.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **31.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **31.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **31.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **31.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **31.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **31.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **31.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **31.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **31.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **31.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **31.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **31.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **31.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **31.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **31.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **31.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **31.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **31.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **31.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **31.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **31.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **31.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **31.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **31.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **31.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **31.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-32 — Dashboard and alert definitions

**Traceability:** C080  
**Objective:** Provide operators with actionable visibility into correctness, saturation, abuse, migration, and dependency health using version-controlled dashboards and alerts.

### Component-specific engineering checklist

- [ ] **32.01** — Define dashboard panels for request rate, ready/timeout/error outcomes, wait-duration percentiles, poll-set sizes, active waiters, and admission rejections.
- [ ] **32.02** — Add security panels for cross-owner refusals, invalid capabilities, malformed requests, policy-denied calls, and audit-sink health.
- [ ] **32.03** — Add migration panels for INV-14 use by approved consumer class, bridge/native INV-15 ratio, parity mismatches, regressions, overdue migrations, and waiver expiry.
- [ ] **32.04** — Add saturation panels for concurrency limit utilization, queue depth/age where present, rejection rate, fairness indicators, and recovery after bursts.
- [ ] **32.05** — Add dependency panels for `pk_core` compatibility, telemetry exporter health, audit backlog, identity verifier health, and runtime adapter errors.
- [ ] **32.06** — Define alerts from service objectives or measured baselines, not arbitrary thresholds; use multi-window/burn-rate logic where appropriate.
- [ ] **32.07** — Distinguish caller misuse/attack indicators from internal software defects so paging routes and severity differ appropriately.
- [ ] **32.08** — Add alerts for missing telemetry/data freshness so silent exporter failure is not interpreted as healthy zero traffic.
- [ ] **32.09** — Link every paging alert to a specific runbook section and dashboard context; non-actionable alerts should not page.
- [ ] **32.10** — Version dashboards and alert rules as code, review changes, and validate syntax/query references in CI.
- [ ] **32.11** — Test alerts using synthetic signals or staging fault injection and verify routing, deduplication, acknowledgement, and recovery notifications.
- [ ] **32.12** — Review alert noise and dashboard usefulness after incidents/releases and record tuning changes with rationale.

### A. Requirements and architecture controls

- [ ] **32.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **32.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **32.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **32.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **32.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **32.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **32.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **32.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **32.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **32.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **32.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **32.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **32.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **32.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **32.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **32.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **32.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **32.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **32.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **32.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **32.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **32.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **32.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **32.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **32.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **32.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **32.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **32.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **32.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **32.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **32.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **32.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **32.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-33 — Incident/runbook package

**Traceability:** C092, C096, C097  
**Objective:** Give operators executable procedures for detection, triage, containment, disablement, rollback, recovery, escalation, and evidence collection.

### Component-specific engineering checklist

- [ ] **33.01** — Define incident entry conditions and severity mapping for widespread timeout, lost readiness, cross-tenant authorization failures, saturation, corrupted artifacts, and migration regressions.
- [ ] **33.02** — Provide first-5-minute triage steps that identify release version, runtime/`pk_core` versions, policy/config version, migration state, process epoch, and active alerts.
- [ ] **33.03** — Provide containment steps for deny-new/drain/emergency-disable modes and state clearly when each is safe to use.
- [ ] **33.04** — Document how to distinguish caller misuse, configuration error, dependency outage, runtime adapter defect, and core polling defect using observable evidence.
- [ ] **33.05** — Provide rollback procedures for configuration, application release, migration bridge/cutover, signing trust material where relevant, and compatible dependency versions.
- [ ] **33.06** — Define recovery validation: smoke tests, readiness/timeout checks, error-rate stabilization, waiter/resource normalization, audit continuity, and migration status reconciliation.
- [ ] **33.07** — Provide data/evidence collection steps including logs, traces, metrics snapshots, audit verification, release manifest, compatibility matrix cell, and fault timeline.
- [ ] **33.08** — Define paging/escalation paths by incident type and explicit handoff points to `pk_core`, runtime/WASI, security, and migration owners.
- [ ] **33.09** — Include communication templates/fields for status updates without embedding sensitive tenant or credential information.
- [ ] **33.10** — Define stop conditions that prevent unsafe repeated retries or uncontrolled rollback loops.
- [ ] **33.11** — Exercise the runbook through game days/tabletops and at least one technical drill using fault injection; capture gaps as tracked work.
- [ ] **33.12** — Version the runbook with the component and require review when lifecycle, policy, migration, or error semantics change.

### A. Requirements and architecture controls

- [ ] **33.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **33.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **33.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **33.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **33.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **33.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **33.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **33.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **33.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **33.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **33.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **33.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **33.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **33.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **33.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **33.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **33.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **33.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **33.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **33.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **33.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **33.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **33.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **33.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **33.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **33.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **33.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **33.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **33.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **33.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **33.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **33.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **33.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-34 — Exception/waiver registry

**Traceability:** C099  
**Objective:** Track every approved deviation from INV-14 migration/security/release policy with accountable ownership, expiry, compensating controls, and automatic enforcement.

### Component-specific engineering checklist

- [ ] **34.01** — Define a machine-readable waiver schema with unique ID, affected consumer/component, requirement waived, rationale, risk statement, owner, approver, issue date, and expiry date.
- [ ] **34.02** — Require explicit scope: environment, tenant, version, interface, and permitted behavior; prohibit broad “all INV-14” waivers unless governance explicitly approves them.
- [ ] **34.03** — Record compensating controls and objective evidence that those controls are active before a waiver can become effective.
- [ ] **34.04** — Prohibit indefinite waivers; require an expiry date and maximum renewal horizon appropriate to the risk tier.
- [ ] **34.05** — Define approval levels by severity/security impact and enforce separation of requester and approver for high-risk waivers.
- [ ] **34.06** — Integrate waiver lookup with migration registry and release/policy enforcement so only covered consumers receive the exception.
- [ ] **34.07** — Generate alerts before expiry and escalate overdue renewal/closure to the accountable owner and governance path.
- [ ] **34.08** — Require renewal to reassess risk and evidence rather than copying the prior approval unchanged.
- [ ] **34.09** — Keep immutable history of created, approved, changed, expired, revoked, and closed waivers.
- [ ] **34.10** — Add CI/policy checks that reject unknown, expired, unsigned/unapproved, or scope-mismatched waiver references.
- [ ] **34.11** — Report active waivers by age, risk, owner, and migration deadline for periodic review.
- [ ] **34.12** — Close a waiver only after evidence shows the underlying requirement is satisfied or the affected consumer is retired.

### A. Requirements and architecture controls

- [ ] **34.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **34.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **34.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **34.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **34.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **34.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **34.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **34.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **34.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **34.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **34.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **34.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **34.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **34.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **34.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **34.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **34.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **34.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **34.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **34.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **34.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **34.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **34.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **34.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **34.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **34.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **34.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **34.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **34.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **34.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **34.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **34.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **34.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## P2-35 — Formal end-of-life policy

**Traceability:** C094, C099  
**Objective:** Convert deprecation into an enforceable retirement program with dated milestones, support boundaries, migration criteria, exceptions, and removal evidence.

### Component-specific engineering checklist

- [ ] **35.01** — Define the EOL scope precisely: INV-14 API versions, package names, adapters, schemas, compatibility bridge behavior, and which support channels are affected.
- [ ] **35.02** — Define lifecycle phases such as deprecated, migration-required, no-new-adoption, maintenance-only, enforcement, end-of-support, and removed.
- [ ] **35.03** — Assign objective dates or version milestones for each phase and identify the authority that can approve changes.
- [ ] **35.04** — Define the no-new-adoption rule and enforce it through policy/CI so new consumers cannot silently begin using INV-14 after the cutoff.
- [ ] **35.05** — Define support obligations in each phase, including security fixes, correctness fixes, compatibility updates, operational assistance, and response targets.
- [ ] **35.06** — Use telemetry and migration registry data to establish completion thresholds before stronger enforcement, while retaining the ability to emergency-disable for security reasons.
- [ ] **35.07** — Define forced-migration criteria and how approved waivers interact with EOL deadlines; waivers must not silently extend global support policy.
- [ ] **35.08** — Publish migration guidance, bridge availability, compatibility requirements, rollback window, and consumer validation steps.
- [ ] **35.09** — Create communication milestones for owners and dependent teams, with acknowledgements tracked through the migration registry or governance system.
- [ ] **35.10** — Define final removal criteria including zero unwaived active consumers, archived evidence, completed runbook updates, and removal of runtime registration/entry points.
- [ ] **35.11** — After removal, retain a tombstone document explaining the last supported version, migration target, archive/evidence location, and unsupported-use policy.
- [ ] **35.12** — Conduct an EOL completion review and archive signed/approved evidence that the removal criteria were satisfied.

### A. Requirements and architecture controls

- [ ] **35.13** — Write normative requirements using **MUST / MUST NOT / SHOULD** language and assign stable requirement IDs; every requirement must map to at least one verification artifact.
- [ ] **35.14** — Define the component boundary, trusted/untrusted inputs, dependencies, outputs, failure domains, and explicit non-goals so adjacent layers do not assume unimplemented guarantees.
- [ ] **35.15** — Define resource ceilings and worst-case behavior relevant to this component (memory, handles, queue entries, serialized size, execution time, retry count, or retained history) and reject over-limit inputs deterministically.
- [ ] **35.16** — Document backward-compatibility and migration impact for the currently hardened INV-14 v4.2.0 behavior; no checklist item may silently redefine ready/timeout/ownership semantics.
- [ ] **35.17** — Identify configuration values, compile-time constants, external policy, and runtime-discovered state separately and define the source of truth for each.

### B. Security and failure-safety controls

- [ ] **35.18** — Update the threat model for this component with abuse cases, cross-tenant risks, integrity/availability risks, trust boundaries, and mitigations; link mitigations back to test IDs.
- [ ] **35.19** — Ensure validation and authorization occur before expensive allocation, external calls, state mutation, or information disclosure; rejected operations must be side-effect bounded.
- [ ] **35.20** — Define fail-closed versus fail-open behavior for dependency outage, malformed state, version mismatch, partial initialization, and corrupted evidence; document every intentional degraded mode.
- [ ] **35.21** — Use stable machine-readable failures with bounded safe detail; do not require callers or operators to parse exception prose to determine remediation.

### C. Implementation and interface quality

- [ ] **35.22** — Keep implementation behind a narrow versioned interface so runtime-specific or provider-specific code does not leak into the core polling semantics.
- [ ] **35.23** — Make state transitions thread-safe/reentrant as applicable and document idempotency for repeated requests, retries, teardown, and rollback operations.
- [ ] **35.24** — Implement deterministic cleanup for every success, refusal, timeout, cancellation, exception, and shutdown path; explicitly test for leaked waiters/handles/buffers.
- [ ] **35.25** — Preserve stable identifiers/correlation across logs, traces, metrics, audit, migration, and test evidence without using unbounded identifiers as metric labels.

### D. Verification and test evidence

- [ ] **35.26** — Add positive, negative, boundary, malformed-input, maximum-size, and zero-value tests specific to this component; each normative requirement must have an evidence reference.
- [ ] **35.27** — Add deterministic regression tests for every defect found while implementing this component, including the minimal reproducer and expected stable result/error code.
- [ ] **35.28** — Run tests under normal and optimized Python execution where Python code is involved, and under every runtime/architecture cell declared supported by the compatibility matrix.
- [ ] **35.29** — Ensure required tests **fail** rather than skip when mandatory dependencies or fixtures are absent in a release/certification job.
- [ ] **35.30** — Produce machine-readable test output plus human-readable summary, environment metadata, dependency versions, source revision, and artifact hashes.

### E. Observability, operations, and governance

- [ ] **35.31** — Define the minimal metrics, structured logs, trace/audit events, and health signals needed to detect this component’s failures without exposing secrets or creating unbounded cardinality.
- [ ] **35.32** — Add operator diagnostics that report the component version, schema/config version, relevant dependency versions, and current safe status while omitting sensitive values.
- [ ] **35.33** — Add or update runbook steps for activation, verification, failure triage, emergency disable/containment, rollback, and recovery validation.
- [ ] **35.34** — Assign an accountable owner and review cadence; unresolved ownership, expired approval, or stale dependency support must block production certification where material.

### F. Release and definition-of-done gates

- [ ] **35.35** — Add the component to the CI/release verifier as a required gate with explicit pass/fail criteria and no manual “assumed pass” path.
- [ ] **35.36** — Update versioned documentation, changelog, architecture/ADR links, compatibility matrix, and migration/EOL material affected by this component.
- [ ] **35.37** — Include new/changed source, schemas, fixtures, tests, generated evidence, and documentation in the release manifest and cryptographic integrity set.
- [ ] **35.38** — Perform clean-environment installation/execution verification from the produced archive rather than only testing the developer working tree.
- [ ] **35.39** — Close the component only when implementation, tests, security review where required, operator evidence, rollback procedure, and traceable acceptance evidence are all present and independently reproducible.

### Required evidence packet

- [ ] **35.40** — Normative requirements/specification and any machine-readable schema/model introduced by this component.
- [ ] **35.41** — Implementation diff/commit plus deterministic build or generation instructions.
- [ ] **35.42** — Positive/negative/boundary test report with exact environment and dependency versions.
- [ ] **35.43** — Security/threat-model delta and review record when the component changes trust, identity, policy, data handling, or supply-chain behavior.
- [ ] **35.44** — Operational evidence: metrics/logs/traces/audit examples, dashboard/runbook update, and rollback or disable procedure as applicable.
- [ ] **35.45** — Release evidence: manifest/hash/signature inclusion, CI gate result, reviewer approval, and compatibility/migration impact statement.

**Component completion count:** 45 checklist controls.

## Final production-certification checklist

- [ ] P0-01 through P0-04 are fully verified; no release relies on absent `pk_core`, prose-only schemas, Python-only WASI assumptions, or an untested INV-15 transition.
- [ ] P1 controls provide authenticated ownership, cancellation, bounded admission, auditable policy/lifecycle behavior, restart/time semantics, accountable ownership, and a tested support matrix.
- [ ] P2 controls provide adjacent integration, protocol conformance, fuzz/concurrency/performance/fault depth, fail-closed CI, SBOM/provenance/signing, governed configuration, redaction, dashboards/runbooks, waivers, and enforceable EOL.
- [ ] The 12 standalone v4.2.0 behavioral tests continue to pass and are supplemented—not replaced—by the new framework/runtime/integration tests.
- [ ] The full `pk_core` 100-item assessment executes against the exact pinned core and produces a non-skipped passing evidence bundle.
- [ ] Real WASI 0.2 interoperability passes on every runtime/architecture cell declared supported.
- [ ] All release artifacts verify from a clean environment using the published manifest, hashes, signatures, dependency lock, schemas, and compatibility metadata.
- [ ] No active production consumer is outside the migration registry; every exception has a live, approved, unexpired waiver.
- [ ] Emergency-disable, rollback, restart recovery, migration rollback, and incident procedures have been exercised rather than only documented.
- [ ] Final approval records identify engineering, security/reliability where applicable, operations, and release/governance reviewers and the exact evidence set they approved.

---

### Boundary note
Encryption at rest, backup, network partition tolerance, and provider failover are not intrinsic properties of the in-memory polling primitive. Where these controls apply through telemetry, audit storage, identity, configuration, runtime, or adjacent-layer integrations, satisfy them in the owning layer and attach objective boundary/integration evidence here rather than claiming an in-memory implementation that does not exist.
